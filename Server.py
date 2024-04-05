from fastapi import FastAPI, Path, Query
from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException
import os
import hashlib

app = FastAPI()

mines = []
rovers = []

rovers_file_path = "rovers.txt"

def increment_string_alpha(s):
    
    chars = [ord(c) - ord('A') for c in s]
    
    # Start incrementing from the last character
    i = len(chars) - 1
    carry = 1  # We start with a carry of 1 because we want to increment by 1
    
    
    while i >= 0 and carry:
        chars[i] += carry  
        
        if chars[i] > 25:  
            chars[i] = 0
            carry = 1
        else:
            carry = 0  
        
        i -= 1  
    
    
    if carry:
        chars.insert(0, 0)  
    
    # Convert the characters back to letters and join them into a string
    incremented_str = ''.join(chr(c + ord('A')) for c in chars)
    return incremented_str



def is_valid_security_code(security_code, mine_serial):
    # Concatenate security code with the mine serial number to create the Temporary Mine Key
    temp_mine_key = mine_serial + security_code
    # Hash the Temporary Mine Key using sha256
    hashed_key = hashlib.sha256(temp_mine_key.encode()).hexdigest()
    # Check if the hashed key has at least 1 leading zeros for testing purposes
    return hashed_key[:5] == '00000'

def disarm_mines_seq(mineserial):

    mine_serial = mineserial
    security_code = "ABCDEF"

    while not is_valid_security_code(security_code, mine_serial):
            
        security_code = increment_string_alpha(security_code)

    return security_code

def find_mine_serial_by_coords(x, y, mines_loc):
    for mine in mines_loc:
        if (x, y) in mine:
            return mine[(x, y)]
    return None

def execute_commands(rover, mines_loc, map, commands, initial_orientation, rows, cols, incoming_x, incoming_y ):
    status = "Not Started"
    current_x, current_y = incoming_x, incoming_y
    current_mine_serial = None
    orientation = initial_orientation
    path = {(incoming_x, incoming_y)}
    blownup = 0
    ex_comm = []

    mines = mines_loc

    for command in commands:
        status = "Moving"
        print(command)
        if command == 'L':
            orientation = (orientation + 1) % 4
            ex_comm.append('L')
        elif command == 'R':
            orientation = (orientation - 1) % 4
            ex_comm.append('R')
        elif command == 'M' and find_mine_serial_by_coords(current_x, current_y, mines) == None:
            ex_comm.append('M')
            if orientation == 0 and current_y < rows - 1:
                print("moving one down")
                current_y += 1
                print(str(current_x) + " " + str(current_y))
            elif orientation == 1 and current_x < cols - 1:
                print("moving one right")
                current_x += 1
                print(str(current_x) + " " + str(current_y))
            elif orientation == 2 and current_y > 0:
                print("moving one up")
                current_y -= 1
                print(str(current_x) + " " + str(current_y))
            elif orientation == 3 and current_x > 0:
                print("moving one left")
                current_x -= 1
                print(str(current_x) + " " + str(current_y))

            if find_mine_serial_by_coords(current_x, current_y, mines):
                serial_number = find_mine_serial_by_coords(current_x, current_y, mines)
                # GetMineSerialNumber example
                print("Landed on mine, Getting mine serial number...")
                print(str(current_y)+", "+str(current_x))
                
                print("Mine Serial Number:", serial_number)
                current_mine_serial = serial_number

        elif command == 'D' and find_mine_serial_by_coords(current_x, current_y, mines):
            ex_comm.append('D')
            # Remove the entry with coordinates (current_x, current_y)
            mines = [mine for mine in mines if (current_x, current_y) not in mine.keys()]
            if(current_mine_serial != None):
                print("Disarming Mine...")
                sec_code=disarm_mines_seq(current_mine_serial)
                print("PIN acknowledged:", sec_code)
            else:
                print("error")
                exit(0)
            continue
        elif command == 'M' and find_mine_serial_by_coords(current_x, current_y, mines):
            ex_comm.append('M')
            print("Rover "+rover +" blew up")
            blownup = 1
            break
        path.add((current_x, current_y))
    status = "Finished"
    if blownup:
        status = "Eliminated"

    return rover, ex_comm, (current_x, current_y), status # Return the commands instead of the direction


# Helper function to read all rovers from the file
def read_all_rovers():
    if not os.path.exists(rovers_file_path):
        return []
    with open(rovers_file_path, "r") as file:
        rovers = file.readlines()
    return [line.strip().split(";") for line in rovers]

# Helper function to save all rovers to the file
def save_all_rovers(rovers):
    with open(rovers_file_path, "w") as file:
        for rover in rovers:
            file.write(";".join(rover) + "\n")

# Map Endpoints
@app.get("/map")
async def get_map():
    # Path to the map.txt file (adjust the path as necessary)
    map_file_path = "map.txt"
    
    # Check if the file exists
    if not os.path.exists(map_file_path):
        print("gotin")
        raise HTTPException(status_code=404, detail="Map file not found.")
    
    # Read the file and parse the map
    with open(map_file_path, "r") as file:
        lines = file.readlines()
        # Skip the first line which contains the dimensions
        map_array = [list(map(int, line.strip().split())) for line in lines[1:]]
    
    return {"map": map_array}

@app.put("/map")
async def update_map(height: int, width: int):
    # Path to the map.txt file (adjust the path as necessary)
    map_file_path = "map.txt"
    
    # Initialize an empty map with the new dimensions
    new_map = [[0 for _ in range(width)] for _ in range(height)]
    
    # Check if the file exists
    if os.path.exists(map_file_path):
        # Read the current map
        with open(map_file_path, "r") as file:
            lines = file.readlines()
            current_height, current_width = map(int, lines[0].strip().split())
            
            # Copy the existing map data to the new map
            for i, line in enumerate(lines[1:]):
                if i < height:  # Avoid index out of range for the new height
                    row_data = list(map(int, line.strip().split()))
                    for j, val in enumerate(row_data):
                        if j < width:  # Avoid index out of range for the new width
                            new_map[i][j] = val
    
    # Write the updated map to the file
    with open(map_file_path, "w") as file:
        file.write(f"{height} {width}\n")
        for row in new_map:
            file.write(' '.join(map(str, row)) + '\n')
    
    return {"message": "Map updated successfully."}


@app.get("/mines")
async def get_mines():
    # Path to the mines.txt file (adjust the path as necessary)
    mines_file_path = "mine.txt"
    mines_list = []

    # Check if the file exists
    if not os.path.exists(mines_file_path):
        raise HTTPException(status_code=404, detail="Mines file not found.")

    # Read and parse the file
    with open(mines_file_path, "r") as file:
        for line in file:
            parts = line.strip().split(":")
            if len(parts) == 3:
                mine_id = int(parts[0])
                coords = parts[1].strip("()").split(",")
                x, y = int(coords[0]), int(coords[1])
                serial_number = parts[2]
                mines_list.append({"id": mine_id, "x": x, "y": y, "serial_number": serial_number})

    return mines_list

@app.get("/mines/{mine_id}")
async def get_mine(mine_id: int = Path(..., description="The ID of the mine to retrieve")):
    # Path to the mines.txt file (adjust the path as necessary)
    mines_file_path = "mine.txt"
    
    # Check if the file exists
    if not os.path.exists(mines_file_path):
        raise HTTPException(status_code=404, detail="Mines file not found.")
    
    # Read and parse the file to find the specific mine
    with open(mines_file_path, "r") as file:
        for line in file:
            parts = line.strip().split(":")
            if len(parts) == 3:
                current_id = int(parts[0])
                # Check if the current mine's ID matches the requested mine_id
                if current_id == mine_id:
                    coords = parts[1].strip("()").split(",")
                    x, y = int(coords[0]), int(coords[1])
                    serial_number = parts[2]
                    return {"id": current_id, "x": x, "y": y, "serial_number": serial_number}
    
    # If the mine with the specified ID was not found, raise a 404 error
    raise HTTPException(status_code=404, detail=f"Mine with ID {mine_id} not found.")


@app.delete("/mines/{mine_id}")
async def delete_mine(mine_id: int):
    # Path to the mines.txt file (adjust the path as necessary)
    mines_file_path = "mine.txt"
    
    # Check if the file exists
    if not os.path.exists(mines_file_path):
        raise HTTPException(status_code=404, detail="Mines file not found.")
    
    mine_found = False
    updated_mines = []

    # Read the current mines, excluding the mine to delete
    with open(mines_file_path, "r") as file:
        for line in file:
            parts = line.strip().split(":")
            if len(parts) == 3:
                current_id = int(parts[0])
                if current_id != mine_id:
                    updated_mines.append(line.strip())
                else:
                    mine_found = True
    
    # If the mine was not found, return a 404 error
    if not mine_found:
        raise HTTPException(status_code=404, detail=f"Mine with ID {mine_id} not found.")
    
    # Write the updated list of mines back to the file
    with open(mines_file_path, "w") as file:
        for mine in updated_mines:
            file.write(f"{mine}\n")
    
    return {"message": f"Mine with ID {mine_id} successfully deleted."}


@app.post("/mines")
async def create_mine(x: int, y: int, serial_number: Optional[str] = None):
    # Path to the mines.txt file
    mines_file_path = "mine.txt"  # Make sure the file name is correct
    
    # Determine the next available mine ID
    next_id = 1
    try:
        with open(mines_file_path, "r") as file:
            lines = file.readlines()
            if lines:
                last_line = lines[-1]
                last_id = int(last_line.split(":")[0])
                next_id = last_id + 1
    except FileNotFoundError:
        # If the file doesn't exist, next_id remains 1
        pass

    # Use mine ID as serial number if not provided
    serial_number = serial_number if serial_number else f"MINE{next_id}"

    # Ensure that a newline exists between each mine entry
    # Check if the last character of the file is not a newline
    newline_prefix = ""
    if os.path.exists(mines_file_path):
        with open(mines_file_path, "rb+") as file:
            file.seek(-1, os.SEEK_END)
            if file.read(1) != b"\n":
                newline_prefix = "\n"

    # Append the new mine to the file with a newline prefix if needed
    with open(mines_file_path, "a") as file:
        file.write(f"{newline_prefix}{next_id}:({x},{y}):{serial_number}\n")

    # Return the new mine's details
    return {"id": next_id, "x": x, "y": y, "serial_number": serial_number}



@app.put("/mines/{mine_id}")
async def update_mine(mine_id: int, x: Optional[int] = Query(None), y: Optional[int] = Query(None), serial_number: Optional[str] = Query(None)):
    mines_file_path = "mine.txt"  # Corrected file name to "mines.txt"
    
    updated = False
    new_lines = []

    # Attempt to read and update the specific mine if the file exists
    if os.path.exists(mines_file_path):
        with open(mines_file_path, "r") as file:
            lines = file.readlines()

        for line in lines:
            parts = line.strip().split(":")  # Use strip() to remove any leading/trailing whitespace or newline characters
            if len(parts) == 3:
                current_id = int(parts[0])
                if current_id == mine_id:
                    # Prepare updated mine details
                    coords = parts[1].strip("()").split(",")
                    current_x, current_y = int(coords[0]), int(coords[1])
                    current_serial = parts[2]

                    # Use provided values or fallback to current ones if not provided
                    new_x = x if x is not None else current_x
                    new_y = y if y is not None else current_y
                    new_serial = serial_number if serial_number is not None else current_serial
                    
                    # Construct the updated mine line
                    updated_line = f"{mine_id}:({new_x},{new_y}):{new_serial}"
                    new_lines.append(updated_line)
                    updated = True
                else:
                    new_lines.append(line.strip())  # Preserve other mines as is
            else:
                raise HTTPException(status_code=500, detail="Invalid file format.")

        if not updated:
            raise HTTPException(status_code=404, detail=f"Mine with ID {mine_id} not found.")
        
        # Write the updated mines back to the file, ensuring only one newline character at the end of each line
        with open(mines_file_path, "w") as file:
            for i, line in enumerate(new_lines):
                # Add a newline character except for the last line
                file.write(line + ("\n" if i < len(new_lines) - 1 else ""))

        return {"id": mine_id, "x": new_x, "y": new_y, "serial_number": new_serial}
    else:
        raise HTTPException(status_code=404, detail="Mines file not found.")

# Additional FastAPI route and function definitions...

@app.get("/rovers")
async def get_rovers():
    rovers = read_all_rovers()
    return [{"rover_id": rover[0], "status": rover[1]} for rover in rovers]

@app.get("/rovers/{rover_id}")
async def get_rover(rover_id: int = Path(..., description="The ID of the rover to retrieve")):
    rovers = read_all_rovers()
    rover = next((rover for rover in rovers if rover[0] == str(rover_id)), None)
    if rover is None:
        raise HTTPException(status_code=404, detail="Rover not found")
    return {"rover_id": rover[0], "status": rover[1], "last_position": rover[2], "commands": rover[3]}

@app.post("/rovers")
async def create_rover(commands: str):
    rovers = read_all_rovers()
    rover_id = str(max([int(rover[0]) for rover in rovers] + [0]) + 1) if rovers else "1"
    rovers.append([rover_id, "Not Started", "(0.0)", commands])
    save_all_rovers(rovers)
    return {"rover_id": rover_id, "status" : "Not Started", "last_position": "(0,0)", "commands": commands}

@app.delete("/rovers/{rover_id}")
async def delete_rover(rover_id: int):
    rovers = read_all_rovers()
    rovers = [rover for rover in rovers if rover[0] != str(rover_id)]
    save_all_rovers(rovers)
    return {"message": f"Rover with ID {rover_id} has been deleted"}

@app.put("/rovers/{rover_id}")
async def update_rover(rover_id: int, status: str = None, last_position: str = None, commands: str = None):
    rovers = read_all_rovers()
    for i, rover in enumerate(rovers):
        print(str(rover[0]) + " , "+ str(rover_id))
        if rover[0] == str(rover_id):
            
            if status is not None: rover[1] = status
            if last_position is not None: rover[2] = last_position
            if commands is not None: rover[3] = commands
            rovers[i] = rover
            save_all_rovers(rovers)
            return rover
    raise HTTPException(status_code=404, detail="Rover not found")

@app.post("/rovers/{rover_id}/dispatch")
async def dispatch_rover(rover_id: int):
    # Reading the rover details
    rovers = read_all_rovers()
    rover = next((rover for rover in rovers if int(rover[0]) == rover_id), None)
    if rover is None:
        raise HTTPException(status_code=404, detail="Rover not found")
    
 
    rover_id, status, position, command_sequence = rover

    # Recover the height, width, and the map array from the map.txt file
    with open('map.txt', 'r') as f:
        lines = f.readlines()
        height, width = map(int, lines[0].split())
        map_array = [list(map(int, line.split())) for line in lines[1:]]

    # Recover the array of mines from the mines.txt file
    mines_loc = []
    with open('mine.txt', 'r') as f:
        for line in f:
            parts = line.strip().split(':')
            if len(parts) == 3:
                mine_id, coords, serial_number = parts
                x, y = map(int, coords.strip('()').split(','))
                mines_loc.append({(x,y):serial_number})
                
    x_str, y_str = position.split(",")

    # Convert the string components into integers
    x = int(x_str)
    y = int(y_str)

    # Assume initial orientation is a global or predefined value
    initial_orientation = 'N'  # North, as an example

    # Call the execute_commands function
    rover_id, executed_command_sequence, new_position, new_status = execute_commands(rover_id, mines_loc, map_array, command_sequence, initial_orientation, height, width, x, y)
    
    # Return the updated rover status
    return {
        "id": rover_id,
        "command_sequence": executed_command_sequence,
        "position": new_position,
        "status": new_status
    }


#id, command_sequence, position, status = execute_commands(rover, initial_orientation, mines, rows, cols)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
