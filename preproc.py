#!/usr/bin/python2
# -*- coding: utf-8 -*-
import cv2
import sys
import numpy as np

def pre_levels(image, minv, maxv, gamma=1.0):
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Get Value channel
    v = img_hsv[:,:,2]

    interval = maxv - minv

    _,v2 = cv2.threshold(v, maxv, 255, cv2.THRESH_TRUNC)
    _,v2 = cv2.threshold(v2, minv, 255, cv2.THRESH_TOZERO)
    cv2.normalize(v2, v2, 0, 255, cv2.NORM_MINMAX)

    img_hsv[:,:,2] = v2
    return cv2.cvtColor(img_hsv, cv2.COLOR_HSV2BGR)

def pre_blur(image):
    blur = cv2.GaussianBlur(image,(5,5),0)
    img_gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
    return (blur, img_gray)

def pre_threshold(image):
    ret,img_thr = cv2.threshold(image,0,255,cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return img_thr

def pre_deskew2(img):
    m = cv2.moments(img)
    rows,cols = img.shape
    if abs(m['mu02']) < 1e-2:
        return img.copy()
    skew = m['mu11']/m['mu02']
    M = np.float32([[1, skew, -0.5*cols*skew], [0, 1, 0]])
    M = cv2.getRotationMatrix2D((cols/2,rows/2),90,1)
    img = cv2.warpAffine(img,M,(cols, rows),flags=cv2.WARP_INVERSE_MAP|cv2.INTER_LINEAR)
    return img

def pre_whiteness(roi):
    r = ((np.array([0,0,0]), np.array([80,80,80])))
    black = cv2.inRange(roi, r[0], r[1])
    black_inv = cv2.bitwise_not(black)

    white = np.zeros((len(roi), len(roi[0]), 3), np.uint8)
    white[:] = (255,255,255)

    roi = cv2.bitwise_and(roi, roi, mask=black_inv)
    white_roi = cv2.bitwise_and(white, white, mask=black)
    return cv2.add(roi, white_roi)

def pre_deskew(img_gray, img_scale, border):
    mask = cv2.inRange(img_gray, 240, 255)

    for m in (img_gray, 255-mask):
        n = cv2.moments(m)
        #print(n['mu11']/n['mu02'])
        contours,_ = cv2.findContours(m, cv2.RETR_EXTERNAL, 2)
        cnt = sorted(contours, key = cv2.contourArea, reverse = True)[0]
        rect = cv2.minAreaRect(cnt)
        if abs(rect[2]) > 45:
            rect = (rect[0], rect[1], 90.0 + rect[2])
        if abs(rect[2]) < 20 and abs(rect[2]) != 0: # != -90.0 and rect[2] != 0.0:
            print('Skew: %.3f°' % rect[2])
            break

    #cv2.imshow('normgr4', m)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    #im = img_scale.copy()
    #peri = cv2.arcLength(box, True)
    #approx = cv2.approxPolyDP(box, 0.02 * peri, True)
    #img_cnt = np.array([ [[0,0]], [[rows,0]], [[rows, cols]], [[0, cols]] ])

    #cv2.drawContours(im,[approx],0,(0,0,255),5)
    #cv2.fillPoly(im, [box], (0,0,255))
    #cv2.drawContours(im, [img_cnt], 0,(0,255,0),2)
    #im = cv2.flip(im, 1)

    if abs(rect[2]) < 20:
        img_scale = img_scale.copy()
        M = cv2.getRotationMatrix2D(rect[0],rect[2],1)
        # img_scale = cv2.warpAffine(img_scale,M,(rows,cols))
        dst = cv2.cv.fromarray(img_scale.copy())
        cv2.cv.WarpAffine(cv2.cv.fromarray(img_scale),dst,cv2.cv.fromarray(M),flags=cv2.INTER_LINEAR+8,fillval=(255,255,255))
        img_scale = np.asarray(dst)
        #img_lev = pre_levels(img_scale, 200, 255)
#        img_lev = pre_levels(img_scale, 0, 170)

        img_scale[:border]    = pre_whiteness(img_scale[:border])
        img_scale[-border:]   = pre_whiteness(img_scale[-border:])
        img_scale[:,-border:] = pre_whiteness(img_scale[:,-border:])
        img_scale[:,:border]  = pre_whiteness(img_scale[:,:border])

    return img_scale

if len(sys.argv) < 2:
    sys.exit(1)

img_rgb = cv2.imread(sys.argv[1])
img_scale = cv2.resize(img_rgb, (0, 0), fx=2.0, fy=2.0)
cols,rows,_ = img_scale.shape

#img_lev = pre_levels(img_scale, 200, 255)
#img_lev = pre_levels(img_scale, 0, 170)
img_lev = pre_levels(img_scale, 230, 255)
_,img_gray = pre_blur(img_lev)

img_scale = pre_deskew(img_gray, img_scale, 20)
img_lev = pre_levels(img_scale, 150, 255)
_,img_gray = pre_blur(img_lev)

img_thr = pre_threshold(img_gray)

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 6))
#kernel = np.ones((2,2), np.uint8)
closed = cv2.morphologyEx(img_thr, cv2.MORPH_CLOSE, kernel)
#closed = cv2.erode(img_thr, kernel, iterations=2)
#closed = img_thr

contours,_ = cv2.findContours(closed.copy(), cv2.RETR_LIST, 4)
cnts = sorted(contours, key = cv2.contourArea, reverse = True)

responses = []

for cnt in cnts:
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    # print(cv2.contourArea(cnt))
    area = cv2.contourArea(cnt)
    if area > 80 and area < 2500:
        [x,y,w,h] = cv2.boundingRect(cnt)

#        cv2.drawContours(img_rgb, [approx], -1, (0, 255, 0), 3)
#        cv2.imshow('norm',img_rgb)
#        key = cv2.waitKey(0)
        if  h>25:
            cv2.rectangle(img_scale,(x,y),(x+w,y+h),(0,0,255),2)
            roi = closed[y:y+h,x:x+w]
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
            roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel)
#            roi = cv2.erode(roi, None, iterations = 2)
            roismall = cv2.resize(roi,(10,10))
#            cv2.imshow('norm3',img_scale)
#            key = cv2.waitKey(0)

#            if key == 27:  # (escape to quit)
#                sys.exit()
            responses.append([x, w, roi, '_'])
#            elif key in keys:
#                responses.append(int(chr(key)))
#                sample = roismall.reshape((1,100))
#                samples = np.append(samples,sample,0)

cv2.imshow('norm', img_scale)
key = cv2.waitKey(0)
