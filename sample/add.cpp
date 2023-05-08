#include <stdio.h>

extern "C" int add(int, int);

int main()
{
	for (int i = 0; i < 10; i++) {
		int x = i*2;
		int y = i+3;
		int z = add(x, y);
		printf("add(%d, %d)=%d (%c)\n", x, y, z, z == x + y ? 'o' : 'x');
	}
}
