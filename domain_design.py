import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from cromosim.domain import Domain
from cromosim.domain import Destination

# To create a Domain object from a background image
dom = Domain(name='room', background='room_3_walls.png', pixel_size=0.1)

wall_color = [0, 0, 0]
door_color = [255, 0, 0]
bottom_xs = (3,37)

door_width = 5

room_width = bottom_xs[1] - bottom_xs[0]
center = bottom_xs[0] + room_width/2
door_start = center - door_width/2
door_end = center + door_width/2

left_bottom_wall = Line2D((bottom_xs[0],door_start),(3,3),linewidth=2)
dom.add_shape(left_bottom_wall, outline_color=wall_color, fill_color=wall_color)

right_bottom_wall = Line2D((door_end, bottom_xs[1]),(3,3),linewidth=2)
dom.add_shape(right_bottom_wall, outline_color=wall_color, fill_color=wall_color)

# To add a destination using a matplotlib shape :
dest_line = Line2D([bottom_xs[0]-2, bottom_xs[1]+2], [2, 2], linewidth=2)
dom.add_shape(dest_line, outline_color=door_color, fill_color=door_color)
# To build the domain :
dom.build_domain()

# To plot the domain : backgroud + added shapes
dom.plot(id=1, title="Domain")

# To create a Destination object towards the door
dest = Destination(name='door', colors=[door_color],
                   excluded_colors=[wall_color])
dom.add_destination(dest)

# To plot the wall distance and its gradient
dom.plot_wall_dist(id=2, step=20,
                   title="Distance to walls and its gradient",
                   savefig=False, filename="room_wall_distance.png")

# To plot the distance to the red door and the correspondant
# desired velocity
dom.plot_desired_velocity('door', id=3, step=20,
                          title="Distance to the destination and desired velocity",
                          savefig=False, filename="room_desired_velocity.png")

print("===> Domain: ", dom)

plt.show()
