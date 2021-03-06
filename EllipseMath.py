import numpy
from math import cos, sin, tan, atan, sqrt, pi, pow
import scipy
import scipy.linalg
from PIL import Image, ImageDraw
from sympy.core import Catalan
from numpy.f2py.auxfuncs import throw_error


def sqrDist( p1, p2 ):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def quadForm(a, b, c, sign):
    return (-1*b + sign*sqrt( b**2 - 4*a*c ) ) / (2*a)

#returns a list of points on the outside of an ellipse given the input coefficients to the ellipse equation
#uses parametric form
def getEllipseOutline( x0, y0, alpha, a, b, fine):
    outline = []
    x = x0 + a * cos(0) * cos(alpha) - b * sin(0) * sin(alpha)
    y = y0 + a * cos(0) * sin(alpha) + b * sin(0) * cos(alpha)
    outline.append( (int(x), int(y)) )
    
    numPoints = int(2 * pi * sqrt( (a**2 + b**2) / 2))
    numPoints = numPoints if fine else 720
    for t in range(1, numPoints):
        theta = t * 2 * pi / numPoints
        x = x0 + a * cos(theta) * cos(alpha) - b * sin(theta) * sin(alpha)
        y = y0 + a * cos(theta) * sin(alpha) + b * sin(theta) * cos(alpha)
        if (int(x), int(y)) != outline[len(outline)-1]:
            outline.append( (int(x), int(y)) )
    return outline

def fillEllipse( im, x0, y0, alpha, a, b, col):
#     '''
#     get points on the outline of the specified ellipse
#     create polygon using those points
#     draw/fill polygon
#     '''
    pnts = getEllipseOutline(x0, y0, alpha, a, b, True)
    draw = ImageDraw.Draw(im)
    draw.polygon(pnts, fill=col)
    

'''
this function will approximate the average curvature at each point along a boundary
by finding the angle formed by that point and its neighbors
'''
def getCurvature( points ):
    totalChange = 0
    prevChange = 0
    firstDeriv = []
    # less than 26
    # more than 8
    d = 10
    for i in range(0, len(points)):
        v1 = (points[(i + d) % len(points)][0] - points[i][0], 
              points[(i + d) % len(points)][1] - points[i][1])
        
        v2 = (points[(i + 2*d) % len(points)][0] - points[(i + d) % len(points)][0], 
              points[(i + 2*d) % len(points)][1] - points[(i + d) % len(points)][1])
        cosTheta = float(v1[0] * v2[0]  +  v1[1] * v2[1]) / ( sqrt(sqrDist(v1, (0,0))) * sqrt(sqrDist(v2, (0,0))) + 0.001 )

        if i > 1:
            firstDeriv.append( cosTheta - prevChange )
            prevChange = cosTheta
            
    sum1 = 0
    for i in range(0, len(firstDeriv)):
        if abs(sin(firstDeriv[i])) < 0.1:
            sum1 += 1
    # calculates the stdev, if desired
#     avg = sum1 / float(len(firstDeriv))
#     sumDiffs = 0
#     for i in range(0, len(firstDeriv)):
#         sumDiffs += (firstDeriv[i] - avg)**2
#     stdv = sqrt( 1 / float(len(firstDeriv)) * sumDiffs )
    return sum1 / float(len(points))

def getCurvature2( points ):
    '''
    approximates curvature in a list of points
    finds the longest chain of points which curve relatively little, divided by the length of the list
    '''
    longestChain = 0
    currentChain = 0
    prevChange = 0
    # less than 26
    # more than 8
    d = 10
    for i in range(0, len(points)):
        v1 = (points[(i + d) % len(points)][0] - points[i][0], 
              points[(i + d) % len(points)][1] - points[i][1])
        
        v2 = (points[(i + 2*d) % len(points)][0] - points[(i + d) % len(points)][0], 
              points[(i + 2*d) % len(points)][1] - points[(i + d) % len(points)][1])
        cosTheta = float(v1[0] * v2[0]  +  v1[1] * v2[1]) / ( sqrt(sqrDist(v1, (0,0))) * sqrt(sqrDist(v2, (0,0))) + 0.001 )

        if abs(cos(cosTheta - prevChange)) > 0.85:
            currentChain += 1
            if currentChain > longestChain:
                longestChain = currentChain
        else:
            currentChain = 0
            
        prevChange = cosTheta
        
    return longestChain / float(len(points))


# uses techniques found in __ to calculate the parameters of a generalized ellipse from
# the parameters to the equation's general conic form. 
def getParameters( A, B, C, D, E, F):
    if B**2 - 4*A*C >= 0:
#         raise Exception("Not an ellipse")
        print("Not an ellipse")
        return 0,0,0,0,0
    M0 = numpy.array([
                      [F, D/2, E/2],
                      [D/2, A, B/2],
                      [E/2, B/2, C]
                      ])
    M = numpy.array([
                      [A, B/2],
                      [B/2, C]
                      ])
    eigs = numpy.linalg.eig(M)[0]
    l1 = 0
    l2 = 0
    
    if abs(eigs[0] - A) <= abs(eigs[0] - C):
        l1 = eigs[0]
        l2 = eigs[1]
    else:
        l1 = eigs[1]
        l2 = eigs[0]
    a = 0
    b = 0
    try:
        a = sqrt( -1* numpy.linalg.det(M0) / (numpy.linalg.det(M) * l1) )
        b = sqrt( -1* numpy.linalg.det(M0) / (numpy.linalg.det(M) * l2) )
    except Exception as e:
        print(e.args)
        print(e)
        return 0, 0, 0, 0, 0

    h = (B*E - 2*C*D)/(4*A*C - B**2)
    k = (B*D - 2*A*E)/(4*A*C - B**2)
    t = (pi/2 - atan( (A-C)/(B+0.000000001) )) / 2
    
    if ( b > a):
        temp = a
        a = b
        b = temp

    return a, b, h, k, t

# calculates the closeness between two lists of points by searching the entirety of list2  
# for a point close to each element in list1
def closeness(list1, list2): #list1 is the fiber outline, list2 is the calculated equation
    goodPoints = 0
    cutOffDist = 3
    if sqrDist( list1[0], list2[0] ) < cutOffDist:
        goodPoints+=1
          
    for i in range(1, len(list1)):
        for j in range(1, len(list2)):
            if (( list1[i], list2[j] ) != ( list1[i-1], list2[j-1] )) & (sqrDist( list1[i], list2[j] ) < cutOffDist):
                goodPoints+=1
                break
    return goodPoints / float(len(list1))

# calculates the closeness between a list of points approximating a fiber-outline and an actual ellipse  
# by checking the sum of the distances from each point in the list to the foci, as compared to the ellipse's
# string length
def closeness2(points, a, b, h, k, t):
    goodPoints = 0
    tolerance = 0.01 # only allow an x% difference
    c = sqrt(a**2 - b**2)
    f1 = ( h - cos(t) * c, k - sin(t) * c )
    f2 = ( h + cos(t) * c, k + sin(t) * c )
    s = 2 * a

    for i in range(0, len(points)):
        distF1 = sqrt(sqrDist(points[i], f1))
        distF2 = sqrt(sqrDist(points[i], f2))
        error1 = ( distF1 + distF2 ) / s
        if abs(error1 - 1) < tolerance:
            goodPoints+=1
    return goodPoints / float(len(points))

# plug the point into the ellipse equation, and see how far off the scale has to be in order for the ellipse
# to go through that point
def closeness3(points, a, b, h, k, t):
    goodPoints = 0
    for i in range(0, len(points)):
        x, y = points[i]
        scale = ((x - h)*cos(t) + (y - k)*sin(t))**2 / a**2 + ((x - h)*sin(t) - (y - k)*cos(t))**2 / b**2
        if abs(scale - 1) < 0.01:
            goodPoints+=1
    return goodPoints / float(len(points))

def getRow( p ):
    x = p[0]
    y = p[1]
    return [ x*x, x*y, y*y, x, y]

# solves the system of ellipse equations for 5 points
def generalizedSolve( pList ):
    
    A = numpy.array([ getRow(pList[0]),
                      getRow(pList[1]),
                      getRow(pList[2]),
                      getRow(pList[3]),
                      getRow(pList[4]) ])
    B = numpy.array( [1, 1, 1, 1, 1] )
    numpy.set_printoptions(8, 1000, 3, 140, True, 'nan', 'inf')
    
    x = numpy.linalg.solve(A, B)
    
    return x

def getSpacedPoints(list1, start, r):
    s = len(list1)
    return [ list1[int(start + r*0/5) % s],
            list1[int(start + r*1/5) % s],
            list1[int(start + r*2/5) % s],
            list1[int(start + r*3/5) % s],
            list1[int(start + r*4/5) % s]  ]


def getBestFit( data, minW, maxL ):
    # list = [ list1[(len(list1)*1)/15], list1[(len(list1)*10)/15], list1[(len(list1)*0)/15], list1[(len(list1)*3)/15], list1[(len(list1)*7)/15]  ]
    approx = []
#     im = Image.new("L", (1400, 800), 0)
    a1 = 0
    b1 = 0
    h1 = 0
    k1 = 0
    t1 = 0
    c = 0
    bestStart = c
    bestPercent = 0.0
    bestScale = 0
    bestP = 0
    count = 0
    bestR = 0
    for i1 in range(3,7):
        r = int( i1/10 * len(data) )
        
        for i in range(0, len(data), 2):
            c = i
            list1 = getSpacedPoints(data, c, r)
            
            try :
                A, B, C, D, E = generalizedSolve( list1 )
                a1, b1, h1, k1, t1 = getParameters(A, B, C, D, E, 1)
                if (a1 == 0) | (b1 == 0):
                    continue
                #a and b are now major and minor axis, respectively
    #             print(a1,b1,"initial a1b1")
    #             avg2 = a1+b1#sqrt((a1**2+b1**2)/2)
    #             scale = avg1/b1
                
                percentSame = 0
                localBestP = -1
                bestLocalNudge = 0
                for pNum in range(0, 5):
                    x = list1[pNum][0]
                    y = list1[pNum][1]
                    for nudge in range(0, 9):
                        h2 = h1 - 1 + nudge % 3
                        k2 = k1 - 1 + nudge / 3
    #                     h2 = h1
    #                     k2 = k1
    
                        '''
                        once it works, try moving the following line outside the nudge loop, to speed it up.
                        '''
                        scale = sqrt( ((x - h2)*cos(t1) + (y - k2)*sin(t1))**2 / a1**2 + ((x - h2)*sin(t1) - (y - k2)*cos(t1))**2 / b1**2 ) 
                        
                        if ( a1*scale > maxL) | (b1*scale < minW):
                            continue
                        
                        approx = getEllipseOutline(h2, k2, t1, a1*scale, b1*scale, False)
                        localSame = closeness(data, approx)
    #                     localSame = closeness2(data, a1*scale, b1*scale, h2, k2, t1)
    #                     localSame = closeness3(data, a1*scale, b1*scale, h2, k2, t1)
    #                     print(localSame)
                        if localSame > percentSame:
                            percentSame = localSame
                            localBestP = pNum
                            bestLocalNudge = nudge
                    # debugging section
    #                 if (i) < -10:
    #                     print("here", percentSame)
    #                     scale = sqrt( ((x - h1)*cos(t1) + (y - k1)*sin(t1))**2 / a1**2 + ((x - h1)*sin(t1) - (y - k1)*cos(t1))**2 / b1**2 ) 
    #                     h2 = h1 - 1 + bestLocalNudge % 3
    #                     k2 = k1 - 1 + bestLocalNudge / 3
    #                     approx = getEllipseOutline(h2, k2, t1, a1*scale, b1*scale, False)
    #                     im = Image.new("RGB", (3152, 2120), 0)
    #                     try:
    #                         
    #     #                         for i1 in range( 0, len(data) ):
    #     #                             p1 = ( data[i1][0], data[i1][1] )
    #     #                             im.putpixel(p1, 255)
    #                         for i2 in range( 0, len(approx) ):
    #     #                         print(approx[i2])
    #                             p1 = ( approx[i2][0], approx[i2][1] )
    #                             im.putpixel(p1, (180,0,0))
    #                         for i3 in range(0, len(data)):
    #                             im.putpixel( data[i3], (0,180,0))
    #                         print(h2, k2, t1, a1*scale, b1*scale)
    #                         im.show()
    #     #                     im.save("temp.bmp")
    #                         input("")
    #                     except IndexError:
    #                         ()
                
                if percentSame > bestPercent:
                    bestPercent = percentSame
                    bestStart = c
                    bestP = localBestP
                    bestNudge = bestLocalNudge
                    bestR = r
                
            except ValueError:
                ()
            except numpy.linalg.linalg.LinAlgError:
                ()
    
#     recalculate using the best version of c found
    if bestPercent > 0.10:
        list1 = getSpacedPoints(data, bestStart, bestR)
        A, B, C, D, E = generalizedSolve( list1 )
        a1, b1, h1, k1, t1 = getParameters(A, B, C, D, E, 1)
        print("...........")
        h1 = h1 - 1 + bestNudge % 3
        k1 = k1 - 1 + bestNudge / 3

        x = list1[bestP][0]
        y = list1[bestP][1]
        scale = sqrt( ((x - h1)*cos(t1) + (y - k1)*sin(t1))**2 / a1**2 + ((x - h1)*sin(t1) - (y - k1)*cos(t1))**2 / b1**2 ) 
        a1 *= scale
        b1 *= scale

        print(a1, b1, h1, k1, t1, "ab")

        return a1, b1, h1, k1, t1 , bestPercent, list1
    return 0,0,0,0,0,0,()

# finds the longest distance in a list of points, as a proxy for the major axis of the ellipse they represent
# it checks the distance between each point and the one (data.length/2) indices away from it.
def longestDist(data):
    maxDist = 0
    for i in range(0, int(len(data)/2)):
        dist = sqrDist(data[i], data[int((i+len(data)/2)) % len(data)])
        if dist > maxDist:
            maxDist = dist
    return sqrt(maxDist)

# gets an initial guess for the Levenburg-Marquedt nonlinear solving algorithm
# the center is estimated as the area center of the list of points
# the angle is the 
def getGuess(data, minW):
    a0 = longestDist(data)/2
    b0 = minW
    xMin = 10e10
    xMax = 0
    yMin = 10e10
    yMax = 0
    for i in range(0, len(data)):
        if data[i][0] < xMin:
            xMin = data[i][0]
        elif data[i][0] > xMax:
            xMax = data[i][0]
        if data[i][1] < yMin:
            yMin = data[i][1]
        elif data[i][1] > yMax:
            yMax = data[i][1]
    h0 = (xMin + xMax) / 2
    k0 = (yMin + yMax) / 2
    if (xMax-xMin) == 0:
        return 0
    t0 = tan((yMax-yMin)/(xMax-xMin))
    
    return a0, b0, h0, k0, t0

def testMethods():
    theta = 0
    a = 90
    b = 40
    h = 0
    k = 0
    t = pi * theta / 180
    c = cos(t)
    s = sin(t)
    
    A = (b*c)**2 + (a*s)**2
    B = -2*c*s*(a**2 - b**2)
    C = (b*s)**2 + (a*c)**2
    D = -2*A*h - k*B
    E = -2*C*k - h*B
    F =-1*(a*b)**2 + A*h**2 + B*h*k + C*k**2
    
    print()
    im = Image.new("L", (800, 800), 0)
    list1 = getEllipseOutline(h, k, t, a, b)
    
    a1, b1, h1, k1, t1 = getParameters(A, B, C, D, E, F)
    list2 = getEllipseOutline(h1, k1, t1, a1, b1)
     
    # print(len(list2))
    for i in range( 0, len(list1) ):
        p1 = ( list1[i][0] + 400, list1[i][1] + 400 )
    #     print(list1[i])
        im.putpixel(p1, 255)
          
    for i in range( 0, len(list2) ):
        p2 = ( list2[i][0] + 400, list2[i][1] + 400 )
        im.putpixel(p2, 90)
      
    im.show()
    