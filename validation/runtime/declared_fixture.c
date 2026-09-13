#define PY_SSIZE_T_CLEAN
#include <Python.h>
static int execute(PyObject *module) { return 0; }
static PyModuleDef_Slot slots[] = {{Py_mod_exec, execute}, {Py_mod_gil, Py_MOD_GIL_NOT_USED}, {0, NULL}};
static struct PyModuleDef definition = {PyModuleDef_HEAD_INIT, "declared_fixture", "Stateless test fixture declaring free-threading support.", 0, NULL, slots};
PyMODINIT_FUNC PyInit_declared_fixture(void) { return PyModuleDef_Init(&definition); }
