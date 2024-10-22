# blender-texture2vgroup

A Blender addon that creates vertex groups based on textures.

## YouTube

https://youtu.be/aZ7ZEkIvtSc

## Features

- Create multiple vertex groups or a single weight-based group from a greyscale texture
- Support for existing textures or loading new ones
- Customizable settings for number of groups, minimum group size, and more
- Works with Blender 4.1.0 and above (and might work with earlier versions)

## Installation

1. Download the `init.py` file and place it in a folder of your choice. (The default Blender addons folder is recommended.)
2. Open Blender and go to Edit > Preferences > Add-ons
3. Click "Install" and select the downloaded file
4. Enable the addon by checking the box next to "Mesh: Vertex Group by Texture"

## Usage

1. Select a mesh object in Object mode
2. Go to Properties > Object Data Properties > Vertex Groups
3. Click on "Create Vertex Groups from Texture"
4. Choose your settings:
   - Texture Source: Use an existing texture or load a new one
   - Use as Weights: Create a single weight-based group or multiple groups
   - Normalize Weights: Set the weights range to between 0.0 and 1.0
   - Number of Groups: How many vertex groups to create (if not using weights)
   - Minimum Group Size: Smallest number of vertices to form a group
   - Base Group Name: Prefix for your vertex group names
5. Click "OK" to generate the vertex groups

## Requirements

- Blender 4.1.0 or higher (will probably work in earlier versions, too)
- Active UV map on the target mesh

## Author

Hennie Kotze
