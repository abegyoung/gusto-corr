void
__stdcall __declspec(dllimport)
bubblesort(
    double *a,
    int n,
    double *b
)
{
    int i, j;
    for (i = 0; i < n - 1; ++i)
    {
        for (j = 0; j < n - i - 1; ++j)
        {
            if (a[j] > a[j + 1])
            {
                double tmp = a[j];
                a[j] = a[j + 1];
                a[j + 1] = tmp;
            }
        }
    }

    for(i=0; i<n; i++)
      b[i] = a[i];
}
