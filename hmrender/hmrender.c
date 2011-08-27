/*
  hmrender.c

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
  This program creates animated height maps using NED data downloaded
  with neddown.py.
 */

#include <stdio.h>

#include <math.h>

#include <ri.h>

#include <gdal/gdal.h>
#include <gdal/cpl_conv.h>

// Data structure containing elevation data
struct data_info_t {
    int origWidth;
    int origHeight;

    int width;
    int height;

    double minEle;
    double maxEle;

    float *eleData;
};

// Utility function to access elevation data at x,y
double eleAt(struct data_info_t *di, int x, int y) {
    return di->eleData[y*di->width + x];
}

// Use GDAL to read the NED data.
int read_ned_data(char *inFName, int stepSize, struct data_info_t *di) {
    
    GDALDatasetH hDataset;
    GDALAllRegister();
    hDataset = GDALOpen(inFName, GA_ReadOnly);
    if (hDataset == NULL) {
        printf("Could not open %s!\n", inFName);
        return 0;
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

    int   nXSize = GDALGetRasterBandXSize( hBand );
    int   nYSize = GDALGetRasterBandYSize( hBand );

    di->origWidth = nXSize;
    di->origHeight = nXSize;
    di->minEle = minEle;
    di->maxEle = maxEle;

    di->width=nXSize/stepSize+1;
    di->height=nYSize/stepSize+1;

    di->eleData = malloc(sizeof(float) * di->width * di->height);

    int tileWidth = nXSize;
    int tileHeight = 1;
    size_t block_size = tileWidth * tileHeight;

    float *pafScanline = (float *) CPLMalloc(sizeof(float)*block_size);

    int curIdx = 0;
    for (int yb=0; yb < nYSize; yb+=stepSize) {
        GDALRasterIO( hBand, GF_Read, 0, yb, tileWidth, 1, 
                      pafScanline, nXSize, 1, GDT_Float32, 
                      0, 0 );

        for (int jj=0; jj< tileWidth; jj += stepSize) {
            di->eleData[curIdx] = pafScanline[jj];
            ++curIdx;
        }
    }
    CPLFree(pafScanline);
    GDALClose(hDataset);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc <2) {
        printf("Must specify a filename prefix.\n");
        return 1;
    }

    char *fnPrefix = argv[1];
    char *inFName = argv[2];


    struct data_info_t di = {0};

    // NED files are 10812x10812
    // That uses a bunch of memory, so only use every 8th data point
    const int stepSize = 8;

    // The elevation data originally ranges from di.minEle to di.maxEle
    // It's scaled to range from 0-1
    // For rendering it's scaled by scale
    const double scale = 25;

    // Read the data and exit on failure
    if (0 == read_ned_data(inFName, stepSize, &di)) {
        printf("Error reading \"%s\"\n", inFName);
        return 1;
    }

    char outputFileName[32] = "";

    // Scale the data into a 200x200 square
    double xMin = -100.0;
    double yMin = -100.0;
    double xMax = 100.0;
    double yMax = 100.0;


    // The x and y increments between each elevation sample
    double xDiff = (xMax - xMin) / di.width;
    double yDiff = (yMax - yMin) / di.height;
    
    RtColor terrainColor = {0.8,1.0,0.8};


    const int numFrames = 36;
    double perFrameRotation = 360.0/numFrames;

    // The number of polygons passed to RiPointsPolygon
    int numPolys = di.width*di.height;

    // The number of vertices in each polygon.
    // Every polygon will be a quad, so this is always 4
    int *numVerts = malloc(sizeof(int)*numPolys);
    for (int i=0;i<numPolys; ++i) {
        numVerts[i] = 4;
    }

    // The indices into verts for each polygon
    int *vertIdx = malloc(sizeof(int)*numPolys*4);

    int cur = 0;
    for (int i=0;i<di.height-1; ++i) {
        for (int j=0;j<di.width-1; ++j) {
            vertIdx[cur++] = i*di.width+j;
            vertIdx[cur++] = (i+1)*di.width+j;
            vertIdx[cur++] = (i+1)*di.width+j+1;
            vertIdx[cur++] = i*di.width+j+1;
        }
    }

    // The actual vertex data
    RtPoint *verts = malloc(sizeof(RtPoint) * numPolys);

    int curVert = 0;
    double x,y,z;
    y = yMin;
    double realScale = scale /(di.maxEle - di.minEle);
    for (int yb=0; yb<di.height; ++yb) {

        x = xMin;
        for (int xb=0; xb<di.width; ++xb) {
            z = eleAt(&di, xb, yb);

            z = (z-di.minEle) * realScale;
            
            verts[curVert][0] = x;
            verts[curVert][1] = z;
            verts[curVert][2] = y;
            ++curVert;
            x += xDiff;
        }
        y += yDiff;
    }
    // Free up memory for use while rendering
    free(di.eleData);

    RiBegin(RI_NULL); {

        RiFormat(512,512, 1);

        RtObjectHandle terrain = RiObjectBegin();
        RiPointsPolygons(numPolys,numVerts,vertIdx, "P", (RtPointer)verts, RI_NULL);
        RiObjectEnd();

        // Loop through each frame
        for (int frame=0; frame<numFrames; ++frame) {
            RiFrameBegin(frame);

            // Specify the output file
            snprintf(outputFileName, 32, "output/%s%04d.jpg", fnPrefix, frame);
            RiDisplay(outputFileName, "jpeg","rgb", "int quality", "90", RI_NULL);

            // Create a lightsource and setup the view
            RiLightSource("distantlight", RI_NULL);
            RiShutter(0.1,0.9);
            RiProjection("perspective", RI_NULL);
            RiTranslate(0.0,0.0,100.0);
            RiRotate(45.0,-1.0,1.0,0.0);
            RiRotate(perFrameRotation * frame, 0,1,0);

            // Create the "world" and one big RiPointsPolygon
            RiWorldBegin(); {
                RiAttributeBegin(); {
                    RiColor(terrainColor);
                    RiSurface("KMVenus",RI_NULL);
                    RiObjectInstance(terrain);
                    /* RiPoints(numPolys, "P", (RtPointer)verts, RI_NULL); */
                } RiAttributeEnd();
                
            } RiWorldEnd();
      
            RiFrameEnd();
        }
    } RiEnd();

    // Free up memory
    free(numVerts);
    free(verts);
    free(vertIdx);
    

    exit(0);
}
