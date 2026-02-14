---
name: quadruped-ctrl
description: Control quadruped robots (Unitree Go2, Petoi Bittle) — gaits, navigation, sensors.
homepage: https://github.com/unitreerobotics/unitree_ros2
metadata:
  {
    "openclaw":
      {
        "emoji": "🐕",
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
            {
              "id": "pip-unitree",
              "kind": "shell",
              "command": "pip install unitree-sdk2py",
              "bins": ["python3"],
              "label": "Install Unitree SDK2 Python bindings (pip)",
            },
          ],
      },
  }
---

# Quadruped Robot Control

Control quadruped robots via ROS 2 or vendor SDKs. Supports Unitree Go2/B2, Petoi Bittle, and any ROS 2-compatible quadruped.

## Unitree Go2 / B2 (via unitree_sdk2py)

### Connection

The robot exposes a network interface. Connect to its Wi-Fi or Ethernet.

```bash
# Default robot IP (Wi-Fi mode)
export ROBOT_IP=192.168.123.161

# Verify connectivity
ping $ROBOT_IP
```

### High-Level Control (recommended)

```python
#!/usr/bin/env python3
"""Send walk commands to Unitree Go2 via the high-level API."""
from unitree_sdk2py.go2.sport import SportClient
import time

client = SportClient()
client.init()

# Stand up
client.stand_up()
time.sleep(1)

# Walk forward at 0.3 m/s for 3 seconds
client.move(0.3, 0.0, 0.0)
time.sleep(3)

# Stop and sit
client.stop_move()
client.stand_down()
```

### Common High-Level Commands

```python
client.stand_up()                    # Stand from sitting
client.stand_down()                  # Sit down
client.move(vx, vy, vyaw)           # Walk: forward, lateral, rotation (m/s, rad/s)
client.stop_move()                   # Emergency stop
client.recovery_stand()              # Recover from fall
client.switch_gait(gait_type)        # 0=idle, 1=trot, 2=run, 3=climb
client.euler(roll, pitch, yaw)       # Tilt body (radians)
client.body_height(height)           # Adjust body height (m)
```

### Sensor Data

```python
from unitree_sdk2py.go2.sport import SportClient

client = SportClient()
client.init()

state = client.get_state()
print(f"Position: {state.position}")
print(f"IMU rpy: {state.imu_state.rpy}")
print(f"Battery: {state.bms_state.soc}%")
print(f"Foot force: {state.foot_force}")
```

## ROS 2 Interface (generic quadrupeds)

### Launch Robot Driver

```bash
# Unitree ROS 2 driver
ros2 launch unitree_ros2 robot.launch.py

# Or any URDF-described quadruped
ros2 launch quadruped_bringup bringup.launch.py
```

### Movement via /cmd_vel

```bash
# Walk forward
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"

# Turn in place
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.5}}"

# Stop
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

### Read Sensors

```bash
# Odometry (position + velocity)
ros2 topic echo /odom --once

# IMU data
ros2 topic echo /imu/data --once

# Joint states
ros2 topic echo /joint_states --once

# Battery
ros2 topic echo /battery_state --once
```

### Autonomous Navigation (Nav2)

```bash
# Launch navigation stack
ros2 launch nav2_bringup navigation_launch.py \
  use_sim_time:=false \
  params_file:=/path/to/nav2_params.yaml

# Send a goal pose
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0}, orientation: {w: 1.0}}}}"

# Cancel navigation
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose --cancel
```

## Petoi Bittle (serial/BLE)

```bash
# Install Petoi SDK
pip install petoi-sdk

# Connect via serial
python3 -c "
from petoi import Bittle
bot = Bittle(port='/dev/ttyUSB0')
bot.command('kup')       # Stand up
bot.command('kwkF')      # Walk forward
bot.command('kbalance')  # Balance
bot.command('krest')     # Rest/sit
"
```

## Safety

- Always test movements in simulation (Gazebo) before running on hardware.
- Keep `client.stop_move()` or Ctrl-C ready as an emergency stop.
- Start with low speeds (< 0.3 m/s) and increase gradually.
- Ensure the robot is on a flat, clear surface for initial tests.
- Monitor battery level — quadrupeds consume significant power.
