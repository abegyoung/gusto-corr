#include <Python.h>

int main() {
    PyObject *pName, *pModule, *pFunc;
    PyObject *pList, *pValue;
    double input_values[] = {1.0, 2.0, 3.0, 4.0, 5.0};
    int num_values = sizeof(input_values) / sizeof(input_values[0]);

    putenv("PYTHONPATH=./");

    // Initialize the Python interpreter
    Py_Initialize();

    // Build the name object
    pName = PyUnicode_FromString("my_python_module");

    // Load the module object
    pModule = PyImport_Import(pName);

    // Check for errors
    if (pModule != NULL) {
        // Get the function from the module
        pFunc = PyObject_GetAttrString(pModule, "increment_values");

        if (pFunc && PyCallable_Check(pFunc)) {
            // Convert C array to a Python List
            pList = PyList_New(num_values);
            for (int i=0; i<num_values; ++i){
                PyList_SetItem(pList, i, PyFloat_FromDouble(input_values[i]));
            }

            // Call the function
            pValue = PyObject_CallFunctionObjArgs(pFunc, pList, NULL);

            // Check for errors
            if (pValue != NULL) {
                // Extract values from the returned list
		for (int i=0; i<num_values; ++i){
                    input_values[i] = PyFloat_AsDouble(PyList_GetItem(pValue, i));
                }
		printf("Modified values:\n");
		for (int i=0; i<num_values; ++i){
                    printf("%f ", input_values[i]);
                }
		printf("\n");
                Py_DECREF(pValue);
            } else {
                PyErr_Print();
            }

            // Clean Up
            Py_DECREF(pList);

        } else {
            if (PyErr_Occurred())
                PyErr_Print();
            fprintf(stderr, "Cannot find function\n");
        
        }
        Py_XDECREF(pFunc);
        Py_DECREF(pModule);
    } else {
        PyErr_Print();
        fprintf(stderr, "Failed to load the Python module\n");
        return 1;
    }

    // Clean Up
    Py_DECREF(pName);

    // Finish the Python interpreter
    Py_Finalize();

    return 0;
}


