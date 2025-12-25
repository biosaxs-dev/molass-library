"""
Simple viewer for the generated comparison images
"""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Load images
img1 = mpimg.imread('comparison1_exponential.png')
img2 = mpimg.imread('comparison2_bimodal.png')
img3 = mpimg.imread('comparison3_various_shapes.png')

# Display in separate windows
fig1 = plt.figure(figsize=(10, 8))
plt.imshow(img1)
plt.axis('off')
plt.title('Comparison 1: Level (a) vs Level (b) with Exponential Distribution', fontsize=14)
plt.tight_layout()

fig2 = plt.figure(figsize=(10, 11))
plt.imshow(img2)
plt.axis('off')
plt.title('Comparison 2: Level (b) with Bimodal Distribution', fontsize=14)
plt.tight_layout()

fig3 = plt.figure(figsize=(10, 8))
plt.imshow(img3)
plt.axis('off')
plt.title('Comparison 3: Effect of Different Distribution Shapes', fontsize=14)
plt.tight_layout()

plt.show()
