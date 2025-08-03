from vedo import Points, Arrows, show
import numpy as np


# Run the simulation
nt = 500
u, v, w, p = cavity_flow(nt, u, v, w, dt, dx, dy, dz, p, rho, nu)

# Prepare the data for visualization
points = np.array([(i, j, k) for i in x for j in y for k in z])
vectors = np.array([(u[k, j, i], v[k, j, i], w[k, j, i]) for i in range(nx) for j in range(ny) for k in range(nz)])

# Create the points and arrows
pts = Points(points, r=4, c='blue')
arrs = Arrows(points, points + vectors, c='red')

# Show the plot
show(pts, arrs, __doc__, axes=1, viewup="z")
