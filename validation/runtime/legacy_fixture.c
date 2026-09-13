#define PY_SSIZE_T_CLEAN
#include <Python.h>
static struct PyModuleDef definition = {PyModuleDef_HEAD_INIT, "legacy_fixture", "Stateless test fixture without a free-threading declaration.", -1, NULL};
PyMODINIT_FUNC PyInit_legacy_fixture(void) { return PyModule_Create(&definition); }
