#include <Python.h>
#include <stdlib.h>
#include <time.h>

int main() {
	PyObject *pName, *pModule, *pFunc;
	PyObject *pArgs, *pValue;
	srand(time(NULL));
	int input1 = (rand() % (10+1));
	int input2 = (rand() % (10+1));
	int result;

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
		pFunc = PyObject_GetAttrString(pModule, "my_python_function");

		if (pFunc && PyCallable_Check(pFunc)) {
			// Build the arguments
			pArgs = PyTuple_New(2);
			PyTuple_SetItem(pArgs, 0, PyFloat_FromDouble(input1));
			PyTuple_SetItem(pArgs, 1, PyFloat_FromDouble(input2));

			// Call the function
			pValue = PyObject_CallObject(pFunc, pArgs);

			// Check for errors
			if (pValue != NULL) {
				result = PyFloat_AsDouble(pValue);
				printf("Sent: %d and %d\n", input1, input2);
				printf("Result of call: %d\n", result);
				Py_DECREF(pValue);
			} else {
				PyErr_Print();
			}

			// Clean Up
			Py_DECREF(pArgs);
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


