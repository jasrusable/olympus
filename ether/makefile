CC=gcc
CCFlags= -std=c99
ValFlags= --tool=memcheck --leak-check=yes --show-reachable=yes --num-callers=20 --track-fds=yes

Libs = -lmongoc `pkg-config --cflags --libs libavformat libchromaprint libavutil libavcodec`

ether: ether.c
	$(CC) $(CCFlags) ether.c -o ether \
		$(Libs)

.PHONY: val
val: ether
	valgrind $(ValFlags) ./ether

.PHONY: oldmethod
oldmethod: oldmethod.c
	$(CC) $(CCFlags) oldmethod.c -o oldmethod \
		$(Libs)
	valgrind $(ValFlags) ./oldmethod

test: test.c
	$(CC) $(CCFlags) ./test.c -o test \
		$(Libs)
	./test
