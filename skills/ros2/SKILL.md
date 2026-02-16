---
name: ros2
description: Control robots, launch nodes, inspect topics and services via the ROS 2 CLI.
homepage: https://docs.ros.org/en/jazzy/
metadata:
  {
    "openclaw":
      {
        "emoji": "🤖",
        "requires": { "bins": ["ros2"] },
        "install":
          [
            {
              "id": "apt-ros2",
              "kind": "shell",
              "command": "sudo apt install -y ros-jazzy-desktop && echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc",
              "bins": ["ros2"],
              "label": "Install ROS 2 Jazzy (apt, Ubuntu 24.04)",
            },
          ],
      },
  }
---

# ROS 2 CLI

Use `ros2` to interact with any ROS 2-based robot: launch nodes, publish/subscribe to topics, call services, inspect parameters, and record bags.

## Environment

Source the workspace before any command:

```bash
source /opt/ros/jazzy/setup.bash
# If using a custom workspace:
source ~/ros2_ws/install/setup.bash
```

## Nodes & Launch

```bash
# List running nodes
ros2 node list

# Get info on a node
ros2 node info /robot_controller

# Launch a full system
ros2 launch <package> <launch_file.py>

# Run a single node
ros2 run <package> <executable>
```

## Topics

```bash
# List all active topics
ros2 topic list -t

# Echo messages on a topic (Ctrl-C to stop)
ros2 topic echo /cmd_vel --once

# Publish a Twist command (move forward)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Check publish rate
ros2 topic hz /odom
```

## Services

```bash
ros2 service list
ros2 service type /spawn_entity
ros2 service call /spawn_entity gazebo_msgs/srv/SpawnEntity "{name: 'bot', xml: '...'}"
```

## Parameters

```bash
ros2 param list /robot_controller
ros2 param get /robot_controller max_speed
ros2 param set /robot_controller max_speed 1.5
```

## Bag Recording (data capture)

```bash
# Record selected topics
ros2 bag record -o scan_session /scan /odom /tf /camera/image_raw

# Play back
ros2 bag play scan_session

# Inspect a bag
ros2 bag info scan_session
```

## Build & Workspace

```bash
# Create a workspace
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash

# Build a single package
colcon build --packages-select my_robot_pkg
```

## Visualization

```bash
# Launch RViz2 for 3D visualization
rviz2

# Launch rqt for GUI tools (topic monitor, plots, etc.)
rqt
```

## Tips

- Always source the workspace before running commands.
- Use `--once` with `topic pub` or `topic echo` to avoid hanging.
- Use `ros2 doctor` to diagnose connectivity issues.
- Simulation: install `ros-jazzy-gazebo-ros-pkgs` for Gazebo integration.
- Prefer `ros2 launch` over manual `ros2 run` for multi-node systems.
