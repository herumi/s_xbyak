#include <stdio.h>

extern "C" int add2(int, int);

int main()
{
	for (int i = 0; i < 10; i++) {
		int x = i*2;
		int y = i+3;
		int z = add2(x, y);
		printf("add2(%d, %d)=%d (%c)\n", x, y, z, z == x + y ? 'o' : 'x');
	}
}
