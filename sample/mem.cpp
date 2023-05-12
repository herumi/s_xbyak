#include <stdio.h>

extern "C" {
extern int g_x;
int inc_and_add(int);
}

int main()
{
	printf("g_x=%d\n", g_x);
	for (int i = 0; i < 10; i++) {
		int x = g_x;
		int y = i*3;
		int z = inc_and_add(y);
		printf("inc_and_add(%d, %d)=%d g_x=%d(%c)\n", x, y, z, g_x, z == x + y + 1? 'o' : 'x');
	}
}
