
RMAN_INC_DIR=/home/jl2/software/3delight-9.0.84/Linux-i686/include
RMAN_LIB_DIR=/home/jl2/software/3delight-9.0.84/Linux-i686/lib

INC_FLAGS=-I$(RMAN_INC_DIR) `gdal-config --cflags`
LIB_FLAGS=-L$(RMAN_LIB_DIR) -lm -l3delight `gdal-config --libs`

hmrender: hmrender.c Makefile
	gcc -o hmrender -g -std=c99 $(INC_FLAGS) hmrender.c $(LIB_FLAGS)


