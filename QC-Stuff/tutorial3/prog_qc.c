#include <Python.h>
#include <time.h>

int main() {
	srand(time(NULL));

	PyObject *pName, *pModule, *pFunc;
	PyObject *pArgs, *pList, *pValue;
	double input1 = 1600000;
	double input2 = 1600000;
	double input3 = 1600000;
	double input4 = 1600000;
	double corrtime = 0.33*5000*1e6/256;


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
		pFunc = PyObject_GetAttrString(pModule, "my_qc_function");

		if (pFunc && PyCallable_Check(pFunc)) {
			// Build the arguments
			pArgs = PyTuple_New(5);
			PyTuple_SetItem(pArgs, 0, PyFloat_FromDouble(input1/corrtime));
			PyTuple_SetItem(pArgs, 1, PyFloat_FromDouble(input2/corrtime));
			PyTuple_SetItem(pArgs, 2, PyFloat_FromDouble(input3/corrtime));
			PyTuple_SetItem(pArgs, 3, PyFloat_FromDouble(input4/corrtime));

			pList = PyList_New(10);

			for (int i=0; i<10; ++i){
				PyList_SetItem(pList, i, PyFloat_FromDouble((rand() % (10000+1000))/corrtime));
			}
			PyTuple_SetItem(pArgs, 4, pList);

			// Call the function
			pValue = PyObject_CallObject(pFunc, pArgs);

			// Check for errors
			if (pValue != NULL) {
				// Extract the new values
				for (int i=0; i<10; ++i){
				    printf("%f ", PyFloat_AsDouble(PyList_GetItem(pValue, i)));
				}
				printf("\n");
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


