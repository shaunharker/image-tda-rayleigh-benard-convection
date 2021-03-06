


import sys
from optparse import OptionParser
from PIL import Image
import numpy as np
import os

import pandas as pd


parser = OptionParser('usage: -d dir --img1 image1 --sub1 sublevel1 --sup1 superlevel1 --img2 image2 --sub2 sublevel2 --sup2 superlevel2 --osub outputsub --osup outputsup'  )

parser.add_option("-d", dest="dir",
                  help="parent directory")
parser.add_option("--img1", dest="img1",
                  help="first image")
parser.add_option("--sub1", dest="sub1",
                  help="first sublevel")
parser.add_option("--sup1", dest="sup1",
                  help="first superlevel")
parser.add_option("--img2", dest="img2",
                  help="second image")
parser.add_option("--sub2", dest="sub2",
                  help="second sublevel")
parser.add_option("--sup2", dest="sup2",
                  help="second superlevel")
parser.add_option("--osub", dest="osub",
                  help="sublevel match")
parser.add_option("--osup", dest="osup",
                  help="superlevel match")

(options, args) = parser.parse_args()


print("########## Matching %s ###########" % options.img1)

# Load the bitmap images.
im1 = Image.open(options.dir + "/" + options.img1)
im1.load()
bmp1 = np.array(im1).astype(int)

im2 = Image.open(options.dir + "/" + options.img2)
im2.load()
bmp2 = np.array(im2).astype(int)

# Compute the sup norm between the two images to use as stability criteria
max_error = np.absolute(np.subtract(bmp1, bmp2)).max()

print("Sup norm: " + str(max_error))

print("Loading data...")

# Load the diamorse data
sub1 = pd.read_csv(options.dir + "/" + options.sub1)
sup1 = pd.read_csv(options.dir + "/" + options.sup1)
sub2 = pd.read_csv(options.dir + "/" + options.sub2)
sup2 = pd.read_csv(options.dir + "/" + options.sup2)


for df in [sub1, sup1, sub2, sup2]: 
  # Add a column of -1 for matchedidx
  df['matchedidx'] = -1
  # Add a column of 0 for radius
  df['radius'] = 0
  # Add zeros for matched birth/death values
  df['matchedbirth'] = 0
  df['matcheddeath'] = 0
  # Convert data frames to numeric
  # df = df.convert_objects(convert_numeric=True)
  df = df.apply(pd.to_numeric, args=('coerce',))
  # MATCH INFINITY POINTS
  df.loc[0,'matchedidx'] = 0


print("...data loaded.")


# BOTTLENECK MATCHES
# For each point in sub1, sup1, look for points in corresponding dimensions in sub2, sup2 
# that are within the max_error. If only one match, this is a matched point by stability.
def bottleneckMatches(pt, data):
  result = data.loc[ \
                   (data['matchedidx'] == -1) & \
                   (data['dim']==pt['dim']) & \
                   (abs(data['birth']-pt['birth']) <= max_error) & \
                   (abs(data['death']-pt['death']) <= max_error) 
                   ]
  if len(result) == 1:
    return result.index.tolist()[0]
  else:
    return -1

def findBottleneckMatches(radius):
  for i in sub1.loc[(sub1['matchedidx']==-1) & (abs(sub1['birth'] - sub1['death']) > 2*max_error)].index:
    if sub1.loc[i,'matchedidx'] == -1:
      match = bottleneckMatches(sub1.iloc[i], sub2.loc[(sub2['matchedidx']==-1)])
      if match > -1:
        sub1.loc[i,'matchedidx'] = match
        sub1.loc[i,'radius'] = radius
        sub1.loc[i,'matchedbirth'] = sub2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sub2.loc[match,'death']
        sub2.loc[match,'matchedidx'] = 1

  for i in sup1.loc[(sup1['matchedidx']==-1) & (abs(sup1['birth'] - sup1['death']) > 2*max_error)].index:
    if sup1.loc[i,'matchedidx'] == -1:
      match = bottleneckMatches(sup1.iloc[i], sup2.loc[(sup2['matchedidx']==-1)])
      if match > -1:
        sup1.loc[i,'matchedidx'] = match
        sup1.loc[i,'radius'] = radius
        sup1.loc[i,'matchedbirth'] = sup2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sup2.loc[match,'death']
        sup2.loc[match,'matchedidx'] = 1

# STABLE GENERATOR MATCHES
# Match the stable generators to within +-2 pixels
def stableGeneratorMatches(pt, data, radius):
  result = data.loc[ 
                   (data['matchedidx'] == -1) & \
                   (data['dim']==pt['dim']) & \
                   (abs(data['b_x']-pt['b_x']) <= radius) & \
                   (abs(data['b_y']-pt['b_y']) <= radius)  & \
                   (abs(data['d_x']-pt['d_x']) <= radius) & \
                   (abs(data['d_y']-pt['d_y']) <= radius) & \
                   (abs(data['birth']-pt['birth']) <= max_error) & \
                   (abs(data['death']-pt['death']) <= max_error)
                   ]

  if len(result) == 1:
    return result.index.tolist()[0]
  else:
    return -1

def findStableGeneratorMatches(radius):
  for i in sub1.loc[(sub1['matchedidx']==-1)].index:
    if sub1.loc[i,'matchedidx'] == -1:
      match = stableGeneratorMatches(sub1.iloc[i], sub2.loc[(sub2['matchedidx']==-1)], radius)
      if match > -1:
        sub1.loc[i,'matchedidx'] = match
        sub1.loc[i,'radius'] = radius
        sub1.loc[i,'matchedbirth'] = sub2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sub2.loc[match,'death']
        sub2.loc[match,'matchedidx'] = 1

  for i in sup1.loc[(sup1['matchedidx']==-1)].index:
    if sup1.loc[i,'matchedidx'] == -1:
      match = stableGeneratorMatches(sup1.iloc[i], sup2.loc[(sup2['matchedidx']==-1)], radius)
      if match > -1:
        sup1.loc[i,'matchedidx'] = match
        sup1.loc[i,'radius'] = radius
        sup1.loc[i,'matchedbirth'] = sup2.loc[match,'birth']
        sup1.loc[i,'matcheddeath'] = sup2.loc[match,'death']
        sup2.loc[match,'matchedidx'] = 1

# PINCH-OFF GENERATOR MATCHES
# Match the pinch-off to within +-2 pixels
def stablePinchOffMatches(pt, data, type, radius):

  if type == 'sub':
    if pt['dim'] == 0:
      result = data.loc[ 
                       (data['matchedidx'] == -1) & \
                       (data['dim']==pt['dim']) & \
                       (abs(data['d_x']-pt['d_x']) <= radius) & \
                       (abs(data['d_y']-pt['d_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                       ]
    else:
      result = data.loc[ 
                       (data['matchedidx'] == -1) & \
                       (data['dim']==pt['dim']) & \
                       (abs(data['b_x']-pt['b_x']) <= radius) & \
                       (abs(data['b_y']-pt['b_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                       ]

  else:
    if pt['dim'] == 0:
      result = data.loc[ 
                       (data['matchedidx'] == -1) & \
                       (data['dim']==pt['dim']) & \
                       (abs(data['d_x']-pt['d_x']) <= radius) & \
                       (abs(data['d_y']-pt['d_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                       ]
    else:
      result = data.loc[ 
                       (data['matchedidx'] == -1) & \
                       (data['dim']==pt['dim']) & \
                       (abs(data['b_x']-pt['b_x']) <= radius) & \
                       (abs(data['b_y']-pt['b_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                       ]

  if len(result) == 1:
    return result.index.tolist()[0]
  else:
    return -1

def findStablePinchOffMatches(radius):
  for i in sub1.loc[(sub1['matchedidx']==-1) & (abs(sub1['birth'] - sub1['death']) > 2*max_error)].index:
    if (sub1.loc[i,'matchedidx'] == -1) & (sub1.loc[i,'dim'] == 0) & (sub1.loc[i,'death'] < 170):
      match = stablePinchOffMatches(sub1.iloc[i], sub2.loc[(sub2['matchedidx']==-1)], 'sub', radius)
      if match > -1:
        sub1.loc[i,'matchedidx'] = match
        sub1.loc[i,'radius'] = radius
        sub1.loc[i,'matchedbirth'] = sub2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sub2.loc[match,'death']
        sub2.loc[match,'matchedidx'] = 1

  for i in sup1.loc[(sup1['matchedidx']==-1) & (abs(sup1['birth'] - sup1['death']) > 2*max_error)].index:
    if (sup1.loc[i,'matchedidx'] == -1) & (sup1.loc[i,'dim'] == 1) & (sup1.loc[i,'death'] < 170):
      match = stablePinchOffMatches(sup1.iloc[i], sup2.loc[(sup2['matchedidx']==-1)], 'sup', radius)
      if match > -1:
        sup1.loc[i,'matchedidx'] = match
        sup1.loc[i,'radius'] = radius
        sup1.loc[i,'matchedbirth'] = sup2.loc[match,'birth']
        sup1.loc[i,'matcheddeath'] = sup2.loc[match,'death']
        sup2.loc[match,'matchedidx'] = 1

  for i in sub1.loc[(sub1['matchedidx']==-1) & (abs(sub1['birth'] - sub1['death']) > 2*max_error)].index:
    if (sub1.loc[i,'matchedidx'] == -1) & (sub1.loc[i,'dim'] == 1) & (sub1.loc[i,'death'] >= 170):
      match = stablePinchOffMatches(sub1.iloc[i], sub2.loc[(sub2['matchedidx']==-1)], 'sub', radius)
      if match > -1:
        sub1.loc[i,'matchedidx'] = match
        sub1.loc[i,'radius'] = radius
        sub1.loc[i,'matchedbirth'] = sub2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sub2.loc[match,'death']
        sub2.loc[match,'matchedidx'] = 1

  for i in sup1.loc[(sup1['matchedidx']==-1) & (abs(sup1['birth'] - sup1['death']) > 2*max_error)].index:
    if (sup1.loc[i,'matchedidx'] == -1) & (sup1.loc[i,'dim'] == 0) & (sup1.loc[i,'death'] >= 170):
      match = stablePinchOffMatches(sup1.iloc[i], sup2.loc[(sup2['matchedidx']==-1)], 'sup', radius)
      if match > -1:
        sup1.loc[i,'matchedidx'] = match
        sup1.loc[i,'radius'] = radius
        sup1.loc[i,'matchedbirth'] = sup2.loc[match,'birth']
        sup1.loc[i,'matcheddeath'] = sup2.loc[match,'death']
        sup2.loc[match,'matchedidx'] = 1



# STABLE ROLL MATCHES
# Match birth generators of death abve the pinch-off level to within +-2 pixels
def stableRollMatches(pt, data, type, radius):
  if type == 'sub':
    result = data.loc[ 
                     (data['matchedidx'] == -1) & \
                     (data['dim']==pt['dim']) & \
                     (abs(data['b_x']-pt['b_x']) <= radius) & \
                     (abs(data['b_y']-pt['b_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                     ]
  else:
    result = data.loc[ 
                     (data['matchedidx'] == -1) & \
                     (data['dim']==pt['dim']) & \
                     (abs(data['d_x']-pt['d_x']) <= radius) & \
                     (abs(data['d_y']-pt['d_y']) <= radius) & \
                     (abs(data['birth']-pt['birth']) <= max_error) & \
                     (abs(data['death']-pt['death']) <= max_error)
                     ]

  if len(result) == 1:
    return result.index.tolist()[0]
  else:
    return -1

def findStableRollMatches(radius):
  for i in sub1.loc[(sub1['matchedidx']==-1)].index:
    if (sub1.loc[i,'matchedidx'] == -1) & (sub1.loc[i,'dim'] == 0) & (sub1.loc[i,'death'] >= 170):
      match = stableRollMatches(sub1.iloc[i], sub2.loc[(sub2['matchedidx']==-1)], 'sub', radius)
      if match > -1:
        sub1.loc[i,'matchedidx'] = match
        sub1.loc[i,'radius'] = radius
        sub1.loc[i,'matchedbirth'] = sub2.loc[match,'birth']
        sub1.loc[i,'matcheddeath'] = sub2.loc[match,'death']
        sub2.loc[match,'matchedidx'] = 1

  for i in sup1.loc[(sup1['matchedidx']==-1)].index:
    if (sup1.loc[i,'matchedidx'] == -1) & (sup1.loc[i,'dim'] == 0) & (sup1.loc[i,'death'] < 170):
      match = stableRollMatches(sup1.iloc[i], sup2.loc[(sup2['matchedidx']==-1)], 'sup', radius)
      if match > -1:
        sup1.loc[i,'matchedidx'] = match
        sup1.loc[i,'radius'] = radius
        sup1.loc[i,'matchedbirth'] = sup2.loc[match,'birth']
        sup1.loc[i,'matcheddeath'] = sup2.loc[match,'death']
        sup2.loc[match,'matchedidx'] = 1


print("Starting matching...")

# MATCHING PROCEDURE
def getMatches(radius):
  print("\nRadius %d...(%d,%d)" % (radius, len(sub1.loc[(sub1['matchedidx']==-1)]),  len(sup1.loc[(sup1['matchedidx']==-1)])))
  findStableGeneratorMatches(radius) # Find the stable generator matches
  print("Stable Generators..." + "(%d,%d)" % (len(sub1.loc[(sub1['matchedidx']==-1)]),  len(sup1.loc[(sup1['matchedidx']==-1)])))
  findBottleneckMatches(radius) # Run bottleneck match first
  print("Bottleneck..." + "(%d,%d)" % (len(sub1.loc[(sub1['matchedidx']==-1)]),  len(sup1.loc[(sup1['matchedidx']==-1)])))
  findStablePinchOffMatches(radius) # Find the stable pinch-off matches
  print("Pinch Offs..." + "(%d,%d)" % (len(sub1.loc[(sub1['matchedidx']==-1)]),  len(sup1.loc[(sup1['matchedidx']==-1)])))
  findStableRollMatches(radius) # Find the stable roll matches
  print("Rolls..." + "(%d,%d)" % (len(sub1.loc[(sub1['matchedidx']==-1)]),  len(sup1.loc[(sup1['matchedidx']==-1)])))

tmpSub = len(sub1.loc[(sub1['matchedidx']==-1)])
tmpSup = len(sup1.loc[(sup1['matchedidx']==-1)])
getMatches(1)

factor=5
radius=0
while ( (len(sub1.loc[(sub1['matchedidx']==-1)]) < tmpSub) | (tmpSup > len(sup1.loc[(sup1['matchedidx']==-1)])) ):
  tmpSub = len(sub1.loc[(sub1['matchedidx']==-1)])
  tmpSup = len(sup1.loc[(sup1['matchedidx']==-1)])
  radius = radius + factor
  getMatches(radius)
  if radius == 5*factor:
    break

print("...matching done!\n\n")



sub1.to_csv(options.dir + "/" + options.osub, index_label="idx")
sup1.to_csv(options.dir + "/" + options.osup, index_label="idx")






