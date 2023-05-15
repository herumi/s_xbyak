#include <vector>
#include <stdio.h>
#include <assert.h>
#include <math.h>

typedef std::vector<float> FloatVec;

extern "C" {

void add_avx(float *z, const float *x, const float *y, size_t n);

}

int main()
{
	const size_t n = 128;
	const float eps = 1e-5;
	FloatVec xv(n), yv(n), zv(n);
	assert(n > 0 && (n % 4) == 0);
	for (size_t i = 0; i < n; i++) {
		xv[i] = i * 1.23f;
		yv[i] = (i + 3) * 2.34f;
	}
	add_avx(zv.data(), xv.data(), yv.data(), n);
	size_t err = 0;
	for (size_t i = 0; i < n; i++) {
		float x = xv[i];
		float y = yv[i];
		float z = zv[i];
		if (fabs(z - (x + y)) > eps) {
			printf("err x=%f y=%f z=%f (%f)\n", x, y, z, x+y);
			err++;
		}
	}
	if (err) {
		printf("err %zd\n", err);
	} else {
		printf("ok\n");
	}
}

