
#define CAPACITY 50000 // Size of the HashTable.

// Defines the HashTable item.
typedef struct Ht_item
{
    char *key;
    char *value;
} Ht_item;

// Defines the LinkedList.
typedef struct LinkedList
{
    Ht_item *item;
    struct LinkedList *next;
} LinkedList;

// Defines the HashTable.
typedef struct HashTable
{
    // Contains an array of pointers to items.
    Ht_item **items;
    LinkedList **overflow_buckets;
    int size;
    int count;
} HashTable;



LinkedList *allocate_list();
LinkedList *linkedlist_insert(LinkedList *, Ht_item *);
Ht_item *linkedlist_remove(LinkedList *);
void free_linkedlist(LinkedList *);
LinkedList **create_overflow_buckets(HashTable *);
void free_overflow_buckets(HashTable *);
Ht_item *create_item(char *, char *);
HashTable *create_table(int );
void free_item(Ht_item *);
void free_table(HashTable *);
void handle_collision(HashTable *, unsigned long, Ht_item *);
void ht_insert(HashTable *, char *, char *);
char *ht_search(HashTable *, char *);
void ht_delete(HashTable *, char *);
void print_search(HashTable *, char *);
void print_table(HashTable *);
