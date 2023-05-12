#include <stdio.h>

extern "C" {
extern int g_x;
int add_x(int);
}

int main()
{
	printf("g_x=%d\n", g_x);
	for (int i = 0; i < 10; i++) {
		g_x = i+5;
		int y = i*3;
		int z = add_x(y);
		printf("add(%d, %d)=%d (%c)\n", g_x, y, z, z == g_x + y ? 'o' : 'x');
	}
}
