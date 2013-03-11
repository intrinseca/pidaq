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

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MAXPATH 16
#define MAX_TRANSFER_LENGTH 512

#define SPI_SPEED 1000000
#define SPI_BITS_PER_WORD 16

typedef uint16_t spi_word_t;

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

    spi_word_t* sample_buf;
    int sample_count;

    pthread_mutex_t sample_buf_mutex;
    sem_t samples_available;
    pthread_t rx_thread;
} PiDAQ;

static void PiDAQ_dealloc(PiDAQ* self);
static PyObject * PiDAQ_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int PiDAQ_init(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_open(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_close(PiDAQ *self);

int extract_samples(spi_word_t* in, int in_offset, PyObject *list, int list_offset, int length)
{
    int i = 0;
    PyObject *new;

    while(i < length)
    {
        //Swap Endianness
        //TODO: Error Checking
        new = PyInt_FromLong(__bswap_16(in[i + in_offset]));
        PyList_SetItem(list, i, new);
        i++;
    }

    return 0;
}

void* spi_read_thread(void* args)
{
    int i;
    int rx_length;
    int rx_remainder;

    struct spi_ioc_transfer transfer;

    DEBUG_STR("Initialising Read Thread\n");

    spi_word_t* tx_buf = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
    spi_word_t* rx_buf = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
    spi_word_t* rx_temp = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));

    memset(tx_buf, 0, sizeof(spi_word_t) * MAX_TRANSFER_LENGTH);
    memset(&transfer, 0, sizeof transfer);

    rx_remainder = 0;
    rx_length = 0;

    transfer.tx_buf = (unsigned long) tx_buf,
    transfer.rx_buf = (unsigned long) rx_buf;
    transfer.speed_hz = SPI_SPEED;
    transfer.bits_per_word = SPI_BITS_PER_WORD;
    transfer.len = sizeof(spi_word_t) * MAX_TRANSFER_LENGTH;

    PiDAQ* self = (PiDAQ*) args;
    DEBUG("%s\n", "Read Thread Running");

    while(!self->closing)
    {
        pthread_mutex_lock(&self->sample_buf_mutex);
        DEBUG("Transferring %d bytes\n", transfer.len);

        if (ioctl(self->fd, SPI_IOC_MESSAGE(1), &transfer) < 1)
        {
            pthread_exit((void*)-1);
        }

        self->sample_count = 0;
        i = 0;

        if(rx_remainder > 0)
        {
            DEBUG("Copying Leftover (%d of %d)\n", (rx_length - rx_remainder), rx_length);
            memcpy(self->sample_buf, rx_temp, sizeof(spi_word_t) * (rx_length - rx_remainder));
            DEBUG("Copying Remainder (%d of %d)\n", rx_remainder, rx_length);
            memcpy(&self->sample_buf[rx_length - rx_remainder], rx_buf, sizeof(spi_word_t) * rx_remainder);
            self->sample_count += rx_length;
            i = rx_remainder;
            rx_remainder = 0;
        }

        while(i < MAX_TRANSFER_LENGTH)
        {
            if(rx_buf[i] != 0)
            {
                //Swap Endianness
                rx_length = __bswap_16(rx_buf[i]);
                DEBUG("Currently have %d samples\n", self->sample_count);
                DEBUG("Found header at %d: %d\n", i, rx_length);
                i++;

                if(rx_length > MAX_TRANSFER_LENGTH)
                    continue;

                //print_array("%3d", &rx_buf[i], MAX_TRANSFER_LENGTH - i);

                if(i + rx_length > MAX_TRANSFER_LENGTH)
                {
                    rx_remainder = (i + rx_length) - MAX_TRANSFER_LENGTH;
                    DEBUG("Length: %3d Remainder: %3d\n", rx_length, rx_remainder);

                    memcpy(rx_temp, &rx_buf[i], sizeof(spi_word_t) * (rx_length - rx_remainder));

                    DEBUG_STR("Copied to temp\n");
                    i += rx_length;
                }
                else
                {
                    rx_remainder = 0;
                    DEBUG("%s\n", "Buffer Complete");

                    memcpy(&self->sample_buf[self->sample_count], &rx_buf[i], sizeof(spi_word_t) * rx_length);

                    self->sample_count += rx_length;
                    i += rx_length;
                }
            }
            else
            {
                i++;
            }
        }

        pthread_mutex_unlock(&self->sample_buf_mutex);

        if(self->sample_count > 0)
        {
            sem_post(&self->samples_available);
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
        self->sample_buf = malloc(MAX_TRANSFER_LENGTH * sizeof(spi_word_t));
        sem_init(&self->samples_available, 0, 0);
        pthread_mutex_init(&self->sample_buf_mutex, NULL);
    }

    DEBUG_STR("Type Initialised");
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
    pthread_create(&self->rx_thread, NULL, spi_read_thread, self);

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
    DEBUG_STR("Waiting\n");
    sem_wait(&self->samples_available);
    DEBUG_STR("Locking\n");
    pthread_mutex_lock(&self->sample_buf_mutex);

    PyObject * rx_list = PyList_New(self->sample_count);
    if(rx_list == NULL)
        return NULL;
    DEBUG_STR("Getting Samples\n");
    extract_samples(self->sample_buf, 0, rx_list, 0, self->sample_count);

    DEBUG_STR("Unlocking\n");
    pthread_mutex_unlock(&self->sample_buf_mutex);

    return rx_list;
}

static PyMethodDef PiDAQ_methods[] = {
        { "open", (PyCFunction) PiDAQ_open, METH_VARARGS | METH_KEYWORDS, PiDAQ_open_doc },
        { "close", (PyCFunction) PiDAQ_close, METH_NOARGS, PiDAQ_close_doc },
        { "get_samples", (PyCFunction) PiDAQ_get_samples, METH_NOARGS, PiDAQ_get_samples_doc },
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
