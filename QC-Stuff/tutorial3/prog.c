#include <Python.h>

int main() {
	PyObject *pName, *pModule, *pFunc;
	PyObject *pArgs, *pValue;
	double input1 = 1600000;
	double input2 = 1600000;
	double corrtime = 0.33*5000*1e6/256;
	double result;

	putenv("PYTHONPATH=./");

	// Initialize the Python interpreter
	Py_Initialize();

	// Build the name object
	pName = PyUnicode_FromString("my_QC_module");

	// Load the module object
	pModule = PyImport_Import(pName);

	// Check for errors
	if (pModule != NULL) {
		// Get the function from the module
		pFunc = PyObject_GetAttrString(pModule, "my_relpower_function");

		if (pFunc && PyCallable_Check(pFunc)) {
			// Build the arguments
			pArgs = PyTuple_New(3);
			PyTuple_SetItem(pArgs, 0, PyFloat_FromDouble(input1));
			PyTuple_SetItem(pArgs, 1, PyFloat_FromDouble(input2));
			PyTuple_SetItem(pArgs, 2, PyFloat_FromDouble(corrtime));




                    for(int i=0; i<10; i++){
			// Call the function
			pValue = PyObject_CallObject(pFunc, pArgs);

			// Check for errors
			if (pValue != NULL) {
				result = PyFloat_AsDouble(pValue);
				printf("Result of call: %f\n", result);
				printf("called with: %f\t%f\n", input1, input2);
				Py_DECREF(pValue);
			} else {
				PyErr_Print();
			}
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


