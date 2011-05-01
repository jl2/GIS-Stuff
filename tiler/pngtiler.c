/*
  pngtiler.c

  Copyright (c) 2011, Jeremiah LaRocco jeremiah.larocco@gmail.com

  Permission to use, copy, modify, and/or distribute this software for any
  purpose with or without fee is hereby granted, provided that the above
  copyright notice and this permission notice appear in all copies.

  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
*/


/*
  This is a utility program to split the NED data downloaded with neddown.py
  into a series of tiled PNG heightmap images that are easier to work with.

  This is somewhat of a rough draft.

  Eventually it will write information about the original dataset to a SQLite
  database so that the tile png images can be cross referenced with the
  original GIS data associated with the NED dataset.

  Currently all GIS data associated with the NED dataset is lost.

 */

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <time.h>

#include <png.h>

#include <gdal/gdal.h>
#include <gdal/cpl_conv.h>

void abort_(const char * s, ...)
{
    va_list args;
    va_start(args, s);
    vfprintf(stderr, s, args);
    fprintf(stderr, "\n");
    va_end(args);
    abort();
}

// For easy switching between 8 and 16-bit pngs
typedef unsigned char sample_t;
#define SAMPLE_MAX ((sample_t)-1)

/*
  Write a png file to fname
  This is very heavily based on http://zarb.org/~gc/html/libpng.html
*/
void write_png(char *fname, int width, int height, png_bytep *row_pointers) {
    png_structp png_ptr;
    png_infop info_ptr;
    int number_of_passes;
        
    FILE *fp = fopen(fname, "wb");
    if (!fp)
        abort_("[write_png_file] File %s could not be opened for writing", fname);

    /* initialize stuff */
    png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);

    if (!png_ptr)
        abort_("[write_png_file] png_create_write_struct failed");

    info_ptr = png_create_info_struct(png_ptr);
    if (!info_ptr)
        abort_("[write_png_file] png_create_info_struct failed");

    if (setjmp(png_jmpbuf(png_ptr)))
        abort_("[write_png_file] Error during init_io");

    png_init_io(png_ptr, fp);


    /* write header */
    if (setjmp(png_jmpbuf(png_ptr)))
        abort_("[write_png_file] Error during writing header");

    png_set_IHDR(png_ptr, info_ptr, width, height,
                 8*sizeof(sample_t), PNG_COLOR_TYPE_GRAY, PNG_INTERLACE_NONE,
                 PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

    png_write_info(png_ptr, info_ptr);


    /* write bytes */
    if (setjmp(png_jmpbuf(png_ptr)))
        abort_("[write_png_file] Error during writing bytes");

    png_write_image(png_ptr, row_pointers);

    /* end write */
    if (setjmp(png_jmpbuf(png_ptr)))
        abort_("[write_png_file] Error during end of write");

    png_write_end(png_ptr, NULL);


    fclose(fp);
}

int main(int argc, char *argv[]) {

    if (argc<2) {
        printf("Not enough arguments given!\n");
        printf("\t%s <output_directory> <arcgrid_file>\n", argv[0]);
        return 1;
    }

    char *dirName = argv[1];
    char *fname = argv[2];

    // Use GDAL to read the NED data.
    GDALDatasetH hDataset;
    GDALAllRegister();
    hDataset = GDALOpen(fname, GA_ReadOnly);
    if (hDataset == NULL) {
        printf("Could not open %s!\n", fname);
        return 1;
    }
    GDALDriverH hDriver;
    hDriver = GDALGetDatasetDriver( hDataset );

    GDALRasterBandH hBand;
    int             bGotMin, bGotMax;
        
    hBand = GDALGetRasterBand( hDataset, 1 );

    // minEle and maxEle are used to scale the output image data
    // between 0 and SAMPLE_MAX
    double minEle = GDALGetRasterMinimum( hBand, &bGotMin );
    double maxEle = GDALGetRasterMaximum( hBand, &bGotMax );

    printf( "Min=%.3f, Max=%.3f\n", minEle, maxEle );
    
    int   nXSize = GDALGetRasterBandXSize( hBand );
    int   nYSize = GDALGetRasterBandYSize( hBand );

    // Just about any tile size should work, but 512x512 seems to
    // be a good trade off between image size and # of images
    int tileWidth = 512;
    int tileHeight = 512;
    
    size_t block_size = tileWidth * tileHeight;

    // Allocate the image buffers
    float *pafScanline = (float *) CPLMalloc(sizeof(float)*block_size);
    sample_t *imageData = (sample_t*)malloc(block_size*sizeof(sample_t));

    // row_pointers will point to the same locations into
    // imageData for every image
    png_bytep *row_pointers = (png_bytep*)malloc(sizeof(png_bytep)*tileHeight);
    for (int i=0; i< tileHeight; ++i) {
        row_pointers[i] = (png_bytep)imageData+(i*tileWidth);
    }

    char ofname[256];
    int xblock = 0;
    int yblock = 0;

    // Note that this is a relatively inefficient way to read the NED data
    // For optimal performance GDALReadBlock should be used instead.
    // Since this program will usually only be run once to get the initial
    // image tiles, I'm not too concerned about it.
    for (int y=0; y< nYSize; y+=tileHeight) {
        // Handle incomplete blocks
        // rSize is the actual height of this block
        int rSize = tileHeight;
        if ((y+tileHeight)> nYSize) {
            rSize = nYSize - y;
        }
        
        xblock = 0;
        for (int x=0; x<nXSize; x+=tileWidth) {
            // Handle incomplete blocks
            // cSize is the actual width of this block
            int cSize = tileWidth;
            if ((x+tileWidth)> nXSize) {
                cSize = nXSize - x;
            }

            // Read the block of NED data
            GDALRasterIO( hBand, GF_Read, x, y, cSize, rSize, 
                          pafScanline, tileWidth, tileHeight, GDT_Float32, 
                          0, 0 );

            // Convert floats between minEle and maxEle into sample_ts
            // between 0 and SAMPLE_MAX
            for (int i = 0; i<rSize*cSize; ++i) {
                float rawVal = pafScanline[i];
                rawVal = (rawVal-minEle)/(maxEle - minEle);
                imageData[i] = (sample_t)(rawVal*SAMPLE_MAX);
            }
            // Write the file
            sprintf(ofname, "%s/tile%04dx%04d.png", dirName, xblock, yblock);
            write_png(ofname, cSize, rSize, row_pointers);

            ++xblock;
        }
        ++yblock;
    }
    
    printf("Done writing data\n");

    // Cleanup and exit
    free(row_pointers);
    free(imageData);
    CPLFree(pafScanline);
    GDALClose(hDataset);
    return 0;
}

