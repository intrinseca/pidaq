#include <Python.h>
#include "structmember.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <linux/types.h>
#include <sys/ioctl.h>

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MAXPATH 16
#define MAX_TRANSFER_LENGTH 1024

#define SPI_SPEED 1000000
#define SPI_BITS_PER_WORD 8

typedef unsigned char spi_word_t;

//#define DEBUG_MODE

#ifdef DEBUG_MODE
#define DEBUG(fmt, args...) printf(fmt, args)
#else
#define DEBUG(fmt, args...)
#endif

typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
    int fd;
} PiDAQ;

static void PiDAQ_dealloc(PiDAQ* self);
static PyObject * PiDAQ_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int PiDAQ_init(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_open(PiDAQ *self, PyObject *args, PyObject *kwds);
static PyObject * PiDAQ_close(PiDAQ *self);

static void
PiDAQ_dealloc(PiDAQ* self)
{
    PiDAQ_close(self);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
PiDAQ_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PiDAQ *self;

    self = (PiDAQ *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->fd = -1;
    }

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

    Py_RETURN_NONE;
}

PyDoc_STRVAR(PiDAQ_close_doc,
    "close()\n\n"
    "Disconnects the object from the interface.\n");

static PyObject *
PiDAQ_close(PiDAQ *self)
{
    DEBUG("%s\n", "Closing Device");

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

int extract_samples(spi_word_t* in, int in_offset, PyObject *list, int list_offset, int length)
{
    int i = 0;
    PyObject *new;

    while(i < length)
    {
//        if(PyList_SetItem(list, i + list_offset, PyInt_FromLong(in[i + in_offset])) != 0)
//        {
//            PyErr_SetString(PyExc_RuntimeError, "Error putting received data item in list");
//            return -1;
//        }
        new = PyInt_FromLong(in[i + in_offset]);
        PyList_Append(list, new);
        Py_DECREF(new);
        i++;
    }

    return 0;
}

static PyObject *
PiDAQ_get_samples(PiDAQ *self)
{
    int i;
    int rx_list_offset;
    int rx_length;
    int rx_remainder;

    struct spi_ioc_transfer transfer;
    spi_word_t tx_buf[MAX_TRANSFER_LENGTH];
    spi_word_t rx_buf[MAX_TRANSFER_LENGTH];

    memset(tx_buf, 0, MAX_TRANSFER_LENGTH);
    memset(&transfer, 0, sizeof transfer);

    rx_length = 0;

    transfer.tx_buf = (unsigned long) tx_buf,
    transfer.rx_buf = (unsigned long) rx_buf;
    transfer.len = MAX_TRANSFER_LENGTH;
    transfer.speed_hz = SPI_SPEED;
    transfer.bits_per_word = SPI_BITS_PER_WORD;

    PyObject * rx_list = PyList_New(rx_length);
    if(rx_list == NULL)
        return NULL;

    rx_list_offset = 0;

    while(rx_length == 0)
    {
        DEBUG("%s\n", "SPI Transfer");

        if (ioctl(self->fd, SPI_IOC_MESSAGE(1), &transfer) < 1)
        {
            PyErr_SetFromErrno(PyExc_IOError);
            return NULL;
        }

        i = 0;

        while(i < MAX_TRANSFER_LENGTH)
        {
            if(rx_buf[i] != 0)
            {
                rx_length = rx_buf[i];
                DEBUG("Found header at %d: %d\n", i, rx_length);

                if(i + rx_length > MAX_TRANSFER_LENGTH)
                {
                    rx_remainder = (i + rx_length + 1) - MAX_TRANSFER_LENGTH;
                    rx_length -= rx_remainder;
                    DEBUG("Remainder: %d\n", rx_remainder);
                }
                else
                {
                    DEBUG("%s\n", "Buffer Complete");
                    rx_remainder = 0;
                }

                if(extract_samples(rx_buf, i + 1, rx_list, rx_list_offset, rx_length) == -1)
                {
                    return NULL;
                }

                i += rx_length;
                rx_list_offset += rx_length;

                if(rx_remainder > 0)
                {
                    transfer.len = rx_remainder;

                    if (ioctl(self->fd, SPI_IOC_MESSAGE(1), &transfer) < 1)
                    {
                        PyErr_SetFromErrno(PyExc_IOError);
                        return NULL;
                    }

                    if(extract_samples(rx_buf, 0, rx_list, rx_list_offset, rx_remainder) == -1)
                    {
                        return NULL;
                    };
                }
            }

            i++;
        }
    }

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

    PiDAQType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&PiDAQType) < 0)
        return;

    m = Py_InitModule3("pidaqif", pidaqif_methods,
                       "Interface module for PiDAQ daughter-board");

    Py_INCREF(&PiDAQType);
    PyModule_AddObject(m, "PiDAQ", (PyObject *)&PiDAQType);
}
