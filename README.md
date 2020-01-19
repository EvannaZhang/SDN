# README

## Code file

- **shortest_paths.py**
- **topo_manager_example.py**
- **ofctl_utils.py**
- **run_mininet.py**

---

## Implementation design

- Shortest Path Calculation by Dijkstra's algorithm and Spanning tree.
- Output topology structure by printing the device and connection.
- Forwarding rule and Flow Table update and output by printing the information.

(Details can be found in report.)

## Instruction for use

This project can be tested on Ubuntu Linux, the testing progress is as following

- Start the controller by:

**ryu-manager --observe-links shortest_paths.py**

- In another terminal, start mininet by:

**sudo python run_mininet.py *+ structure name* ** (after this command, the forwarding and topology tables are printed)

- Then you can use ping and link up/down commands to do test.

A parameter *flooding_flag* is set to be False as default, you can change it to True to test the broadcast storm case.

## Problem description

There is still a problem that the host can not be deleted even we add a delete event function.