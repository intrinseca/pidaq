#include <Python.h>
#include "structmember.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <linux/types.h>
#include <sys/ioctl.h>
#include <byteswap.h>
#include <pthread.h>
#include <semaphore.h>
#include <errno.h>

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MAXPATH 16
#define MAX_TRANSFER_LENGTH 512

#define SPI_SPEED 1000000
//The STM32 is sending in 16 bit per word mode, but the RPi only supports
//up to 8. Luckily, receiving twice as many 8 bit words works almost the same.
//This parameter was not error checked when the code was first written
//(This causes the need to swap the bytes)
#define SPI_BITS_PER_WORD 8

typedef uint16_t spi_word_t;

#define SAMPLE_BUFFER_LEN MAX_TRANSFER_LENGTH * sizeof(spi_word_t) * 10

#define DEBUG_MODE

#ifdef DEBUG_MODE
#define DEBUG(fmt, args...) printf(fmt, args)
#else
#define DEBUG(fmt, args...)
#endif

#define DEBUG_STR(str) DEBUG("%s", str)

typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
    volatile int closing;
    int fd;

    unsigned char digital_in;

    unsigned char digital_mask;
    unsigned char digital_conf;
    unsigned char digital_out;

    spi_word_t* sample_buf;
    int sample_count;

    pthread_mutex_t sample_buf_mutex;
    sem_t samples_available;
    pthread_t rx_thread;
    volatile unsigned int rx_thread_error;
} PiDAQ;

static void PiDAQ_dealloc(PiDAQ* self);
static PyObject * PiDAQ_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int PiDAQ_init(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_open(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_close(PiDAQ *self);

int extract_samples(spi_word_t* in, int in_offset, PyObject *list, int list_offset, int length)
{
    int i = 0;
    spi_word_t sample;
    PyObject *new;

    while(i < length)
    {
        //Swap Endianness
        //TODO: Error Checking
        //Swap the bytes
        sample = __bswap_16(in[i + in_offset]);

        //Mask off header
        new = PyInt_FromLong(sample & ~0xF000);
        PyList_SetItem(list, i, new);
        i++;
    }

    return 0;
}

char extract_digital(spi_word_t* in)
{
    char result = 0;

    result |= (__bswap_16(in[0]) & 0x7000) >> 7;
    result |= (__bswap_16(in[1]) & 0x7000) >> 10;
    result |= (__bswap_16(in[2]) & 0x7000) >> 13;

    return result;
}

void read_thread_error(PiDAQ* self, const char * message)
{
    DEBUG_STR(message);
    DEBUG_STR(strerror(errno));
    DEBUG_STR("\n");
    self->rx_thread_error = 1;
}

void* spi_read_thread(void* args)
{
    int i;
    int rx_length;
    int rx_remainder;
    int have_lock = 0;

    struct spi_ioc_transfer transfer;

    PiDAQ* self = (PiDAQ*) args;

    DEBUG_STR("Initialising Read Thread\n");

    spi_word_t* tx_buf = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
    if(tx_buf == NULL)
    {
        read_thread_error(self, "Cannot allocate tx_buf");
        pthread_exit((void*)-1);
    }

    spi_word_t* rx_buf = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
    if(rx_buf == NULL)
    {
        read_thread_error(self, "Cannot allocate rx_buf");
        pthread_exit((void*)-1);
    }

    spi_word_t* rx_temp = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
    if(rx_temp == NULL)
    {
        read_thread_error(self, "Cannot allocate rx_temp");
        pthread_exit((void*)-1);
    }

    memset(tx_buf, 0, sizeof(spi_word_t) * MAX_TRANSFER_LENGTH);
    memset(&transfer, 0, sizeof(transfer));

    rx_remainder = 0;
    rx_length = 0;

    transfer.tx_buf = (unsigned long) tx_buf,
    transfer.rx_buf = (unsigned long) rx_buf;
    transfer.speed_hz = SPI_SPEED;
    transfer.bits_per_word = SPI_BITS_PER_WORD;
    transfer.len = sizeof(spi_word_t) * MAX_TRANSFER_LENGTH;

    DEBUG("%s\n", "Read Thread Running");

    while(!self->closing)
    {
        DEBUG("\nT %4d ", transfer.len);

        //Set the tx_buf for transmitted commands
        tx_buf[0] = __bswap_16(0x8000 | self->digital_mask); //Set mask
        tx_buf[1] = __bswap_16(0xA000 | self->digital_conf); //Set configuration
        tx_buf[2] = __bswap_16(0xC000 | self->digital_out); //Set data

        if (ioctl(self->fd, SPI_IOC_MESSAGE(1), &transfer) < 1)
        {
            read_thread_error(self, "SPI ioctl failed: ");
            pthread_exit((void*)-1);
        }

        if(!have_lock)
        {
            pthread_mutex_lock(&self->sample_buf_mutex);
            have_lock = 1;
        }

        i = 0;

        //TODO: Error on overflow, currently just resets

        if(rx_remainder > 0)
        {
            if(self->sample_count + rx_length > SAMPLE_BUFFER_LEN)
            {
                DEBUG_STR("!!OO!! ");
                self->sample_count = 0;
            }

            DEBUG("< %4d ", (rx_length - rx_remainder));
            memcpy(&self->sample_buf[self->sample_count], rx_temp, sizeof(spi_word_t) * (rx_length - rx_remainder));
            DEBUG("> %4d ", rx_remainder);
            memcpy(&self->sample_buf[self->sample_count + rx_length - rx_remainder], rx_buf, sizeof(spi_word_t) * rx_remainder);

            //Extract digital input
            self->digital_in = extract_digital(&self->sample_buf[self->sample_count]);

            //Update start pointer
            self->sample_count += rx_length;
            i = rx_remainder;
            rx_remainder = 0;
        }

        while(i < MAX_TRANSFER_LENGTH)
        {
            //Length has high bit set (which is swapped in order)
            if((rx_buf[i] & 0x0080) == 0x0080)
            {
                //Swap Endianness, mask off header bits
                rx_length = __bswap_16(rx_buf[i]) & ~0xF000;
                DEBUG("G %4d ", self->sample_count);
                DEBUG("H %4d @ %4d ", rx_length, i);
                i++;

                if(rx_length > MAX_TRANSFER_LENGTH)
                    continue;

                //print_array("%3d", &rx_buf[i], MAX_TRANSFER_LENGTH - i);

                if(i + rx_length > MAX_TRANSFER_LENGTH)
                {
                    rx_remainder = (i + rx_length) - MAX_TRANSFER_LENGTH;
                    DEBUG("R %4d ", rx_remainder);

                    memcpy(rx_temp, &rx_buf[i], sizeof(spi_word_t) * (rx_length - rx_remainder));

                    i += rx_length;
                }
                else
                {
                    rx_remainder = 0;
                    DEBUG("%s", "B ");

                    if(self->sample_count + rx_length > SAMPLE_BUFFER_LEN)
                    {
                        DEBUG_STR("OOOOOO ");
                        self->sample_count = 0;
                    }

                    memcpy(&self->sample_buf[self->sample_count], &rx_buf[i], sizeof(spi_word_t) * rx_length);

                    //Extract digital input
                    self->digital_in = extract_digital(&self->sample_buf[self->sample_count]);

                    //Update start pointer
                    self->sample_count += rx_length;
                    i += rx_length;
                }
            }
            else
            {
                i++;
            }
        }

        if(self->sample_count > 0)
        {
            have_lock = 0;
            pthread_mutex_unlock(&self->sample_buf_mutex);
        }
    }

    DEBUG("%s\n", "Exiting Read Thread");
    free(tx_buf);
    free(rx_buf);
    free(rx_temp);
    pthread_exit(0);
}

void print_array(const char* format, spi_word_t* array, int length)
{
    int i;

    printf("Array (%d) -> [", length);

    for(i = 0; i < length; i++)
    {
        printf(format, __bswap_16(array[i]));
        printf(", ");
    }

    printf("%s", "]\n");
}

static void
PiDAQ_dealloc(PiDAQ* self)
{
    PiDAQ_close(self);
    free(self->sample_buf);
    sem_destroy(&self->samples_available);
    pthread_mutex_destroy(&self->sample_buf_mutex);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
PiDAQ_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PiDAQ *self;

    self = (PiDAQ *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->fd = -1;
        self->closing = 0;

        self->digital_in = 0;
        self->digital_mask = 0;
        self->digital_conf = 0;
        self->digital_out = 0;

        self->sample_buf = malloc(SAMPLE_BUFFER_LEN);
        self->rx_thread_error = 0;
        sem_init(&self->samples_available, 0, 0);
        pthread_mutex_init(&self->sample_buf_mutex, NULL);
    }

    DEBUG_STR("Type Initialised\n");
    return (PyObject *)self;
}

static int
PiDAQ_init(PiDAQ *self, PyObject *args, PyObject *kwds)
{
    int bus = -1;
    int client = -1;
    static char *kwlist[] = { "bus", "client", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|ii:__init__", kwlist, &bus, &client))
        return -1;

    if (bus >= 0)
    {
        PiDAQ_open(self, args, kwds);
        if (PyErr_Occurred())
            return -1;
    }

    DEBUG_STR("Object Initialised\n");
    return 0;
}

PyDoc_STRVAR(PiDAQ_open_doc,
        "open(bus, device)\n\n"
        "Connects to the specified PiDAQ device.\n"
        "open(X,Y) will open /dev/spidev-X.Y\n");

static PyObject *
PiDAQ_open(PiDAQ *self, PyObject *args, PyObject *kwds)
{
    int bus, device;
    char path[MAXPATH];
    static char *kwlist[] = { "bus", "device", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "ii:open", kwlist, &bus, &device))
    {
        return NULL;
    }

    DEBUG_STR("Opening Device\n");

    if (snprintf(path, MAXPATH, "/dev/spidev%d.%d", bus, device) >= MAXPATH)
    {
        PyErr_SetString(PyExc_IOError, "Bus and/or device number is invalid.");
        return NULL;
    }

    if ((self->fd = open(path, O_RDWR, 0)) < 0)
    {
        char err_str[20 + MAXPATH];
        sprintf(err_str, "Can't open device: %s", path);
        PyErr_SetString(PyExc_IOError, err_str);
        return NULL;
    }

    self->sample_count = 0;
    //TODO: Error Handling
    DEBUG("%s\n", "Starting Read Thread\n");
    if(pthread_create(&self->rx_thread, NULL, spi_read_thread, self) != 0)
    {
        PyErr_SetFromErrno(PyExc_IOError);
    }

    Py_RETURN_NONE;
}

PyDoc_STRVAR(PiDAQ_close_doc,
        "close()\n\n"
        "Disconnects the object from the interface.\n");

static PyObject *
PiDAQ_close(PiDAQ *self)
{
    DEBUG("%s\n", "Closing Device");

    self->closing = 1;
    pthread_join(self->rx_thread, NULL);

    if ((self->fd != -1) && (close(self->fd) == -1))
    {
        PyErr_SetFromErrno(PyExc_IOError);
        return NULL;
    }

    self->fd = -1;

    Py_RETURN_NONE;
}

PyDoc_STRVAR(PiDAQ_get_samples_doc,
        "get_samples() -> [samples]\n\n"
        "Get a block of samples from the device.\n");

static PyObject *
PiDAQ_get_samples(PiDAQ *self)
{
    if(self->rx_thread_error)
    {
        PyErr_SetString(PyExc_IOError, "Error in SPI Read Thread");
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    DEBUG_STR("l      ");
    pthread_mutex_lock(&self->sample_buf_mutex);
    Py_END_ALLOW_THREADS

    PyObject * rx_list = PyList_New(self->sample_count);
    if(rx_list == NULL)
        return NULL;
    DEBUG("g %4d ", self->sample_count);
    extract_samples(self->sample_buf, 0, rx_list, 0, self->sample_count);
    self->sample_count = 0;
    DEBUG_STR("u      ");
    pthread_mutex_unlock(&self->sample_buf_mutex);

    return rx_list;
}

PyDoc_STRVAR(PiDAQ_get_digital_in_doc,
        "get_digital_in() -> value\n\n"
        "Get the most recent value of the digital inputs on the device.\n");

static PyObject *
PiDAQ_get_digital_in(PiDAQ *self)
{
    Py_BEGIN_ALLOW_THREADS
    pthread_mutex_lock(&self->sample_buf_mutex);
    Py_END_ALLOW_THREADS

    PyObject * ret = PyInt_FromLong(self->digital_in);

    pthread_mutex_unlock(&self->sample_buf_mutex);

    return ret;
}

PyDoc_STRVAR(PiDAQ_set_digital_out_doc,
        "set_digital_out(data, [mask, [configuration]])\n\n"
        "Set the data and configuration of the digital port\n");

static PyObject *
PiDAQ_set_digital_out(PiDAQ *self, PyObject *args, PyObject *kwds)
{
    char mask, conf, data;
    static char *kwlist[] = {"data", "mask", "configuration", NULL };

    mask = 0;
    conf = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "b|bb:set_digital_out", kwlist, &data, &mask, &conf))
    {
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    pthread_mutex_lock(&self->sample_buf_mutex);
    Py_END_ALLOW_THREADS

    self->digital_mask = mask;
    self->digital_conf = conf;
    self->digital_out = data;

    pthread_mutex_unlock(&self->sample_buf_mutex);

    Py_RETURN_NONE;
}

static PyMethodDef PiDAQ_methods[] = {
        { "open", (PyCFunction) PiDAQ_open, METH_VARARGS | METH_KEYWORDS, PiDAQ_open_doc },
        { "close", (PyCFunction) PiDAQ_close, METH_NOARGS, PiDAQ_close_doc },
        { "get_samples", (PyCFunction) PiDAQ_get_samples, METH_NOARGS, PiDAQ_get_samples_doc },
        { "get_digital_in", (PyCFunction) PiDAQ_get_digital_in, METH_NOARGS, PiDAQ_get_digital_in_doc },
        { "set_digital_out", (PyCFunction) PiDAQ_set_digital_out, METH_VARARGS | METH_KEYWORDS, PiDAQ_set_digital_out_doc },
        {NULL}  /* Sentinel */
};

static PyTypeObject PiDAQType = {
        PyObject_HEAD_INIT(NULL)
        0,                         /*ob_size*/
        "pidaqif.PiDAQ",           /*tp_name*/
        sizeof(PiDAQ),             /*tp_basicsize*/
        0,                         /*tp_itemsize*/
        (destructor)PiDAQ_dealloc, /*tp_dealloc*/
        0,                         /*tp_print*/
        0,                         /*tp_getattr*/
        0,                         /*tp_setattr*/
        0,                         /*tp_compare*/
        0,                         /*tp_repr*/
        0,                         /*tp_as_number*/
        0,                         /*tp_as_sequence*/
        0,                         /*tp_as_mapping*/
        0,                         /*tp_hash */
        0,                         /*tp_call*/
        0,                         /*tp_str*/
        0,                         /*tp_getattro*/
        0,                         /*tp_setattro*/
        0,                         /*tp_as_buffer*/
        Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
        "PiDAQ Interface",         /* tp_doc */
        0,                         /* tp_traverse */
        0,                         /* tp_clear */
        0,                         /* tp_richcompare */
        0,                         /* tp_weaklistoffset */
        0,                         /* tp_iter */
        0,                         /* tp_iternext */
        PiDAQ_methods,             /* tp_methods */
        0,                         /* tp_members */
        0,                         /* tp_getset */
        0,                         /* tp_base */
        0,                         /* tp_dict */
        0,                         /* tp_descr_get */
        0,                         /* tp_descr_set */
        0,                         /* tp_dictoffset */
        (initproc)PiDAQ_init,      /* tp_init */
        0,                         /* tp_alloc */
        PiDAQ_new,                 /* tp_new */
};

static PyMethodDef pidaqif_methods[] = {
        {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initpidaqif(void)
{
    PyObject* m;

    if (PyType_Ready(&PiDAQType) < 0)
        return;

    m = Py_InitModule3("pidaqif", pidaqif_methods,
            "Interface module for PiDAQ daughter-board");

    Py_INCREF(&PiDAQType);
    PyModule_AddObject(m, "PiDAQ", (PyObject *)&PiDAQType);
}
