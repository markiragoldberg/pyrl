

# this file has too much stuff in it. need to learn to import.

import libtcodpy as libtcod
#used sqrt at some points
import math
#used textwrap for messages
import textwrap
#used this to save/load
import shelve

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#GUI element constants
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30

#amount of healing player gets from a healing potion
HEAL_AMOUNT = 40
#stats of spell-scroll effects, otherwise self-explanatory
LIGHTNING_DAMAGE = 40
LIGHTNING_RANGE = 5
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 25
#xp required to reach level 2
LEVEL_UP_BASE = 200
#additional xp required to level up for each previous level gained
LEVEL_UP_FACTOR = 150

#Maximum pth length a monster will tolerate when using A* to chase the player
#Higher values may lead to extreme detours or monsters forgetting where they're going.
#Conversely, lower values may make it hard for distant monsters to chase the player.
#Really low values will result in monsters ignoring obvious flanking routes.
MAX_ASTAR_PATH_LENGTH = 20

TURNS_MONSTERS_CHASE_PLAYER_AFTER_LOSING_CONTACT = 5
SHOUT_RADIUS = 7


MAP_WIDTH = 80
MAP_HEIGHT = 43

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

FOV_ALGO = libtcod.FOV_PERMISSIVE_8
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

LIMIT_FPS = 20

######################
# message(): log an in-game message, deleting ones that overflow GUI
######################

def message(new_msg, color = libtcod.white):
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
	
	for line in new_msg_lines:
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
		game_msgs.append((line, color))
	

######################
# Rect: a rectangular region of the map
######################

class Rect:
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h
		
	#get center coordinates
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)
		
	#check if Rect intersects another Rect
	def intersect(self, other):
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and 
		self.y1 <= other.y2 and self.y2 >= other.y1)

################
# Mapgen functions
################

#create a room using Rect
def create_room(room):
	global map
	for x in range(room.x1 + 1, room.x2):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].sight_blocker = False
			map[x][y].move_blocker = False

def create_h_tunnel(x1, x2, y):
	global map
	for x in range(min(x1,x2), max(x1,x2)+1):
		map[x][y].sight_blocker = False
		map[x][y].move_blocker = False
		

def create_v_tunnel(y1, y2, x):
	global map
	for y in range(min(y1,y2), max(y1,y2)+1):
		map[x][y].sight_blocker = False
		map[x][y].move_blocker = False
			
##############
# object: movable thing with a character representing it on the map
##############

class object:
	def __init__(self, x, y, char, name, color, move_blocker=False, always_visible=False, fighter = None, ai = None, item = None, equipment = None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.move_blocker = move_blocker
		self.always_visible = always_visible
		
		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self
		self.ai = ai
		if self.ai:
			self.ai.owner = self
		self.item = item
		if self.item:
			self.item.owner = self
		self.equipment = equipment
		if self.equipment:
			self.equipment.owner = self
			#equipment is always an item
			self.item = Item()
			self.item.owner = self
	
	#move by the given amount if not blocked, returning True if it worked
	def move(self, dx, dy):
		if not move_blocker(self.x + dx, self.y + dy):
			self.x += dx
			self.y += dy
			return True
		else:
			return False
			
	#approximate a straight line path using "vector mathematics"
	#now able to maneuver around trivial obstacles, like corners.
	def move_towards(self, target_x, target_y):
		#get vector, distance
		distx = target_x - self.x 
		disty = target_y - self.y 
		#using circledist here because it's prettier and has little impact
		distance = math.sqrt(distx ** 2 + disty ** 2)
		
		#figure out what grid-locked move approximates a step along the vector?
		dx = int(round(distx / distance))
		dy = int(round(disty / distance))
		
		#try alternative moves if the direct approach doesn't work
		if self.move(dx, dy) != True:
			if abs(dx) == abs(dy):
				#diagonal didn't work, so try moving only along the more distant axis
				#if that doesn't work, try the other way
				if abs(distx) > abs(disty):
					dy = 0
					if self.move(dx,dy) != True:
						dx = 0
						dy = -1 if disty < 0 else 1
						self.move(dx,dy)
				else:
					dx = 0
					if self.move(dx,dy) != True:
						dy = 0
						dx = -1 if distx < 0 else 1
						self.move(dx,dy)
			elif abs(dx) > abs(dy) and disty != 0:
				#x-dir alone didn't work, so try adding a y-component
				dy = -1 if disty < 0 else 1
				if self.move(dx,dy) != True:
					#diag didn't work, so remove the x-component
					dx = 0
					self.move(dx,dy)
			elif abs(dy) > abs(dx) and distx != 0:
				#as above, but with x and y reversed
				dx = -1 if distx < 0 else 1
				if self.move(dx,dy) != True:
					dy = 0
					self.move(dx,dy)
	
	#move to dest using A* pathfinding
	def move_astar(self, target):
		fov = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
		
		#set move, sight blockers
		for y1 in range(MAP_HEIGHT):
			for x1 in range(MAP_WIDTH):
				libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].sight_blocker, not map[x1][y1].move_blocker)
			
		#Treat tiles occupied by monsters as move blocked
		for obj in objects:
			if obj.move_blocker and obj != self and obj != target:
				libtcod.map_set_properties(fov, obj.x, obj.y, True, False)
				
		#Allocate path. Use roguelike geometry (diagonals = cardinals).
		my_path = libtcod.path_new_using_map(fov, 1.0)
		
		#Compute path
		libtcod.path_compute(my_path, self.x, self.y, target.x, target.y)
		
		#Confirm path was found, and is short, then take step.
		if not libtcod.path_is_empty(my_path) and libtcod.path_size(my_path) < MAX_ASTAR_PATH_LENGTH:
			x, y = libtcod.path_walk(my_path, True)
			if x or y:
				#self.move takes dx, dy so don't use that
				self.x = x
				self.y = y
		#If the path is bad, take direct path to player.
		#This happens if, say, player is behind a monster in a corridor.
		else:
			self.move_towards(target.x, target.y)
			
		#Deallocate path memory
		libtcod.path_delete(my_path)
			
		
	#Distance to object using roguelike geometry.
	def distance_to(self, other):
		return self.distance(other.x, other.y)
		
	#Distance to tile using roguelike geometry.
	#In a world where squares are circles, dist is just greater of x or y.
	def distance(self, x, y):
		dx = x - self.x
		dy = y - self.y 
		return max( abs(dx), abs(dy) )
		
	def draw(self):
		#draw this object at its current map position
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and map[self.x][self.y].explored)):
			libtcod.console_set_default_foreground(console, self.color)
			libtcod.console_put_char(console, self.x, self.y, self.char, libtcod.BKGND_NONE)
			
	def send_to_back(self):
		#send this monster to the front of the list so it's drawn first
		#used to make corpses overdrawn by living creatures
		#seems like a hack tbqh
		#does result in bad behavior: corpses overwritten on the map,
		#but also listed first when looking at tile with a living creature
		global objects
		objects.remove(self)
		objects.insert(0, self)
		
	def clear(self):
		#erase this object from the console
		if libtcod.map_is_in_fov(fov_map, self.x, self.y):
			libtcod.console_put_char_ex(console, self.x, self.y, '.', libtcod.white, libtcod.dark_blue)
		
###########################
# Fighter: combat component of a combat-capable object
###########################

class Fighter:
	def __init__(self, hp, defense, power, xp, death_function=None):
		self.base_max_hp = hp
		self.hp = hp
		self.base_defense = defense
		self.base_power = power
		self.xp = xp
		self.death_function = death_function
		
	#calculate effective values of many stats based on equipment
	@property
	def max_hp(self):
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus
		
	@property
	def power(self):
		bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_power + bonus
		
	@property
	def defense(self):
		bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
		return self.base_defense + bonus
		
	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage
			
			#death handling
			if self.hp <= 0:
				if self.owner != player: #give player xp for kill
					player.fighter.xp += self.xp
				function = self.death_function
				if function is not None:
					function(self.owner)
			
	def attack(self, target):
		damage = self.power - target.fighter.defense
		
		if damage > 0:
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points!')
			target.fighter.take_damage(damage)
		else:
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' to no effect.')
			
	def heal(self, amount):
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp
			
##############################
# cast_heal(): heal the player (e.g. for using a potion)
##############################

def cast_heal():
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'cancelled'
	message('Your wounds start to feel better!', libtcod.light_violet)
	player.fighter.heal(HEAL_AMOUNT)
	
#############################
# cast_lightning(): hit the monster nearest the player with lightning bolt
#############################

def cast_lightning():
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None:
		message('No enemy is close enough to strike.', libtcod.light_blue)
		return 'cancelled'
		
	message('A lightning bolt strikes the ' + monster.name + ' with a thunderous zap! The damage is ' + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
	monster.fighter.take_damage(LIGHTNING_DAMAGE)
	
#############################
# cast_confuse(): hit the monster nearest to the player with confusion
#############################

def cast_confuse():
	message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'cancelled'
		
	#Swap out the monster's brain with temporary porridge
	old_ai = monster.ai
	monster.ai = ConfusedMonster(old_ai)
	monster.ai.owner = monster
	message('The eyes of the ' + monster.name + ' look vacant, as it starts to stumble around!', libtcod.light_green)
	
##################################
# cast_fireball(): target arbitrary point near player with a fireball
##################################

def cast_fireball():
	message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	
	message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
	
	for object in objects:
		if object.distance(x,y) <= FIREBALL_RADIUS and object.fighter:
			message('The ' + object.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
			object.fighter.take_damage(FIREBALL_DAMAGE)
	
#############################
# closest_monster(): return the closest monster to the player within range
#############################

def closest_monster(max_range):
	closest_enemy = None
	closest_dist = max_range + 1
	
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			dist = player.distance_to(object)
			if dist < closest_dist:
				closest_dist = dist
				closest_enemy = object
	return closest_enemy
			
############################
# Item: inventory item component of an object that can be picked up
############################

class Item:
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		#add to inventory, remove from map
		if len(inventory) >= 26:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)
			#auto-equip to empty slots
			equipment = self.owner.equipment
			if equipment and get_equipped_in_slot(equipment.slot) is None:
				equipment.equip()
			
	def drop(self):
		#dequip item if necessary
		if self.owner.equipment:
			self.owner.equipment.dequip()
		#add item to map, remove item from player inventory
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x 
		self.owner.y = player.y 
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
			
	def use(self):
		if self.owner.equipment:
			self.owner.equipment.toggle_equip()
			return
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner) #consume items on use
				
###################################################
# Equipment: item that can be equipped. Automatically adds the item component.
###################################################

class Equipment:
	def __init__(self, slot, power_bonus = 0, defense_bonus = 0, max_hp_bonus = 0):
		self.slot = slot
		self.power_bonus = power_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
		self.is_equipped = False
		
	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()
			
	def equip(self):
		old_equipment = get_equipped_in_slot(self.slot)
		if old_equipment is not None:
			old_equipment.dequip()
		self.is_equipped = True
		message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
	
	def dequip(self):
		if not self.is_equipped: return
		self.is_equipped = False
		message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
		
###################################
# get_equipped_in_slot(): returns the equipment in a slot, or None
###################################

def get_equipped_in_slot(slot):
	for obj in inventory:
		if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
			return obj.equipment
	return None
	
################################################################
# get_all_equipped(): gets a list of all the object's equipped items
# it does an object because I guess the tutorial wants to encourage
# you to implement monsters equipping items?
################################################################

def get_all_equipped(obj):
	if obj == player:
		equipped_list = []
		for item in inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return [] #no monster equipment :(

############################
# BasicMonster: AI for "charge and melee" enemies
############################

class BasicMonster:
	def __init__(self):
		self.turns_to_chase_player = 0
		
	def take_turn(self):
		monster = self.owner
		#simple reciprocal fov by mooching off player's fov_map
		
		#reset chase timer if monster can see the player
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			#alert nearby monsters if monster wasn't already alert
			if self.turns_to_chase_player == 0:
				message("The " + self.owner.name + " shouts!", libtcod.red)
				for object in objects:
					if object != monster and object.distance(monster.x, monster.y) <= SHOUT_RADIUS and object.ai:
						object.ai.turns_to_chase_player = TURNS_MONSTERS_CHASE_PLAYER_AFTER_LOSING_CONTACT
			self.turns_to_chase_player = TURNS_MONSTERS_CHASE_PLAYER_AFTER_LOSING_CONTACT
			
		#chase the player if the chase timer is nonzero (and decrement timer too)
		if self.turns_to_chase_player > 0:
			self.turns_to_chase_player -= 1
			#close on distant player
			if monster.distance_to(player) >= 2:
				monster.move_astar(player)
			#kill adjacent, alive player
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)
				
###############################
# ConfusedMonster: AI for monsters recently hit by Confuse scroll
###############################

class ConfusedMonster:
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns

	def take_turn(self):
		if self.num_turns > 0:
			#randomwalk and decrement timer
			self.owner.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1))
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)
	
#############################
# player_death(player): handle player death (lose game)
#############################

def player_death(player):
	global game_state
	message('You died!',libtcod.red)
	game_state = 'dead'
	
	#represent player as corpse
	player.char = '%'
	player.color = libtcod.dark_red

#############################
# boss_death(player): handle boss death (wins game atm)
#############################

def boss_death(boss):
	monster_death(boss)
	message('You\'ve killed the dragon, and won the game! Press escape to exit.', libtcod.gold)
	
	
	
	
####################################
# monster_death(monster): handle monster death
####################################

def monster_death(monster):
	message(monster.name.capitalize() + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.',libtcod.orange)
	
	#convert monster to a corpse
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.move_blocker = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	#send monster to front of list so it's drawn before/under other objects
	monster.send_to_back()
	
	
###########################
# Tile: immovable square of map terrain
###########################

#note that tiles don't have a character or color right now

class Tile:
	def __init__(self, move_blocker, sight_blocker = None):
		self.move_blocker = move_blocker
		
		#by default, tile blocks sight only if it blocks movement
		if sight_blocker is None: sight_blocker = move_blocker
		self.sight_blocker = sight_blocker
		
		self.explored = False
		
######################
# move_blocker(x, y) [function]: check if a location blocks movement
######################
		
def move_blocker(x, y):
	if map[x][y].move_blocker:
		return True
		
	for object in objects:
		if object.move_blocker and object.x == x and object.y == y:
			return True
			
	return False
	
#################################################
# random_choice_index(): choose one index from a list of chances, raffle-style
#################################################

def random_choice_index(chances):
	dice = libtcod.random_get_int(0, 1, sum(chances))
	
	running_sum = 0
	choice = 0
	for w in chances:
		running_sum += w
		
		if dice <= running_sum:
			return choice
		choice += 1
		
##################################################
# random_choice(): choose one string from a list of (string, chance), raffle-style
# in other words it's the previous function but it documents what the options represent better
##################################################

def random_choice(chances_dict):
	chances = chances_dict.values()
	strings = chances_dict.keys()
	
	return strings[random_choice_index(chances)]

################################
# place_objects(): spawns monsters and items in existing rooms.
################################

def place_objects(room):
	#define the possible random results by dungeon level
	
	#monster spawning rules
	max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
	monster_chances = {}
	monster_chances['orc'] = 80 #orcs always have 80 chances
	#15 troll chances at dungeon level 3, 30 chances at dlvl 5, etc.
	monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
	
	#item spawning rules
	max_items = from_dungeon_level([[1, 1], [2, 4]])
	item_chances = {}
	item_chances['heal'] = 35
	item_chances['confuse'] = from_dungeon_level([[10, 2]])
	item_chances['lightning'] = from_dungeon_level([[25, 4]])
	item_chances['fireball'] = from_dungeon_level([[25, 6]])
	item_chances['sword'] = from_dungeon_level([[5, 4]])
	item_chances['shield'] = from_dungeon_level([[15, 8]])
	
	#place monsters first
	num_monsters = libtcod.random_get_int(0, 0, max_monsters)
	
	for i in range (num_monsters):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		if not move_blocker(x, y):
			monster_roll = random_choice(monster_chances)
			if monster_roll == 'orc':
				fighter_component = Fighter(hp = 20, defense = 0, power = 4, xp = 35, death_function = monster_death)
				ai_component = BasicMonster()
			
				monster = object(x, y, 'o', 'orc', libtcod.desaturated_green, move_blocker = True, fighter = fighter_component, ai = ai_component)
			elif monster_roll == 'troll':
				fighter_component = Fighter(hp = 30, defense = 2, power = 8, xp = 100, death_function = monster_death)
				ai_component = BasicMonster()
				monster = object(x, y, 'T', 'troll', libtcod.darker_green, move_blocker = True, fighter = fighter_component, ai = ai_component)
			
			objects.append(monster)
	
	#place items second
	num_items = libtcod.random_get_int(0, 0, max_items)
	
	for i in range(num_items):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		#only place items if the tile is not blocked (possibly a wall)
		#ideally this would distinguish between wall-like terrain and monsters but it doesn't matter much
		if not move_blocker(x, y):
			itemRoll = random_choice(item_chances)
			if itemRoll == 'heal':
				item_component = Item(use_function = cast_heal)
				item = object(x, y, '!', 'healing potion', libtcod.violet, item = item_component, always_visible = True)
			elif itemRoll == 'lightning':
				item_component = Item(use_function = cast_lightning)
				item = object(x, y, '?', 'scroll of lightning bolt', libtcod.light_blue, item = item_component, always_visible = True)
			elif itemRoll == 'fireball':
				item_component = Item(use_function = cast_fireball)
				item = object(x, y, '?', 'scroll of fireball', libtcod.light_yellow, item = item_component, always_visible = True)
			elif itemRoll == 'confuse':
				item_component = Item(use_function = cast_confuse)
				item = object(x, y, '?', 'scroll of confuse monster', libtcod.light_green, item = item_component, always_visible = True)
			elif itemRoll == 'sword':
				equipment_component = Equipment(slot='right hand', power_bonus = 3)
				item = object(x, y, '/', 'sword', libtcod.sky, equipment = equipment_component)
			elif itemRoll == 'shield':
				equipment_component = Equipment(slot='left hand', defense_bonus = 1)
				item = object(x, y, '[', 'shield', libtcod.darker_orange, equipment = equipment_component)
			objects.append(item)
			#hack to ensure monsters are drawn over items
			item.send_to_back()
			
###########################################
# from_dungeon_level(): returns a value that depends on the current dungeon level from a table
###########################################

def from_dungeon_level(table):
	for (value, level) in reversed(table):
		if dungeon_level >= level:
			return value
	return 0

############################
# Make_map(): Creates the dungeon map
############################

def make_map():
	global map, objects, stairs
	
	objects = [player]
	
	#default = void that blocks nothing
	map = [[ Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]
			
	rooms = []
	num_rooms = 0
	
	for r in range(MAX_ROOMS):
		#make random stats for another random room
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
		y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h -  1)
		
		new_room = Rect(x, y, w, h)
		
		room_intersects = False
		for other_room in rooms:
			if new_room.intersect(other_room):
				room_intersects = True
				break
		
		if not room_intersects:
			create_room(new_room)
			
			(new_x, new_y) = new_room.center()
			
			#place player in first room
			if num_rooms == 0:
				player.x = new_x
				player.y = new_y
			#rooms 2 ... MAX_ROOMS must have a connecting corridor
			else:
				(prev_x, prev_y) = rooms[num_rooms-1].center()
				
				#randomize whether vertical or horizontal displacement is corrected first
				if libtcod.random_get_int(0, 0, 1) == 1:
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				else:
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)
			#place monsters in the room
			place_objects(new_room)
			#need to track placed rooms
			rooms.append(new_room)
			num_rooms += 1
	#last room only has stairs if there's no boss
	if dungeon_level < 9:
		stairs = object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible = True)
		objects.append(stairs)
		stairs.send_to_back() #tired of this hack
	else:
		#place boss
		stairs = None
		x = libtcod.random_get_int(0, new_room.x1+1, new_room.x2-1)
		y = libtcod.random_get_int(0, new_room.y1+1, new_room.y2-1)
		#BIG BUG this while loop sometimes loops endlessly, probably (not 100% certain this caused it but it obviously theoretically could and I didn't add any other looping structure when it happened)
		#Conversely, spawning the monster on top of another monster will look strange, but probably mostly work okay.
		#A better fix is to give place_objects parameter(s) that tell it what kind of things to place...
		#while move_blocker(x, y):
			#x = libtcod.random_get_int(0, new_room.x1+1, new_room.x2-1)
			#y = libtcod.random_get_int(0, new_room.y1+1, new_room.y2-1)
		fighter_component = Fighter(hp = LIGHTNING_DAMAGE * 3 + 1, defense = 4, power = 20, xp = 0, death_function = boss_death)
		ai_component = BasicMonster()
		boss = object(x, y, 'D', 'the dragon', libtcod.red, move_blocker = True, fighter = fighter_component, ai = ai_component)
		objects.append(boss)
		
	
###############################
# next_level(): place player on next dungeon level
###############################

def next_level():
	global dungeon_level
	message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
	#heal 50% hp
	player.fighter.heal(player.fighter.max_hp / 2)
	
	message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
	dungeon_level += 1
	make_map()
	initialize_fov()
	#this is a good time to autosave, in case of a fatal bug
	save_game()
	
########################################
# check_level_up(): increase the player's character level if eligible
########################################

def check_level_up():
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	if player.fighter.xp >= level_up_xp:
		player.level += 1
		player.fighter.xp -= level_up_xp
		message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
		
		#ask player to improve a stat
		#i'm pretty sure these options are terribly unbalanced and agility is the god stat right now
		choice = None
		while choice == None:
			choice = menu('Level up! Choose a stat to raise:\n',
			['Constitution (+20 HP, from ' + str(player.fighter.base_max_hp) + ')',
			'Strength (+1 attack, from ' + str(player.fighter.base_power) + ')',
			'Agility (+1 defense, from ' + str(player.fighter.base_defense) + ')'], LEVEL_SCREEN_WIDTH)
		
		if choice == 0:
			player.fighter.base_max_hp += 20
			player.fighter.hp += 20
		elif choice == 1:
			player.fighter.base_power += 1
		elif choice == 2:
			player.fighter.base_defense += 1
			
###########################
# render_bar(): render a colored bar (e.g. for health in GUI)
###########################

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color, text_color):
	bar_width = int(float(value) / maximum * total_width)
	
	#draw maximum bar
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
	
	#draw filled portion of bar
	if bar_width > 0:
		libtcod.console_set_default_background(panel, bar_color)
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
		
	#draw label with exact numbers and what the bar represents
	libtcod.console_set_default_foreground(panel, text_color)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))
	
##########################
# render_all(): Renders everything to the visible console
##########################


def render_all():
	global fov_recompute
	global fov_map
	
	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
		
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			wall = map[x][y].sight_blocker
			visible = libtcod.map_is_in_fov(fov_map, x, y)
			if not visible:
				if map[x][y].explored:
					if wall:
						libtcod.console_put_char_ex(console, x, y, "#", color_dark_wall, libtcod.BKGND_SET)
					else:
						libtcod.console_put_char_ex(console, x, y, ".", color_dark_ground, libtcod.BKGND_SET)
			else:
				if wall:
					libtcod.console_put_char_ex(console, x, y, "#", color_light_wall, libtcod.BKGND_SET)
				else:
					libtcod.console_put_char_ex(console, x, y, ".", color_light_ground, libtcod.BKGND_SET)
				map[x][y].explored = True
				
	#quick fix to "item is drawn instead of the monster standing on it" issue
	objects.sort(key = lambda x: x.move_blocker)
				
	for object in objects:
		object.draw()
				
	libtcod.console_blit(console, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
	
	#redraw GUI elements
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	#show player's current HP
	render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.red, libtcod.darkest_red, libtcod.white)
	#show dungeon level
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(dungeon_level))
	#show names of objects at cursor if they're in fov
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
	#show short message log
	y = 1
	for(line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	
	#blit GUI to root
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
	
#######################
# menu(): show a menu and also allow interaction with it
#	header: the menu's title
#	options: a list of strings that can be selected from the menu
#	width: the width of the menu panel
#######################

def menu(header, options, width):
	if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
	
	#calculate height of panel
	header_height = libtcod.console_get_height_rect(console, 0, 0, width, SCREEN_HEIGHT, header)
	if header == '':
		header_height = 0
	height = len(options) + header_height
	
	#draw to additional console to preserve current console
	window = libtcod.console_new(width, height)
	
	#print header with wrap
	libtcod.console_set_default_foreground(window, libtcod.white)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
	
	#print formatted menu options
	y = header_height
	letter_index = ord('a')
	for option_text in options:
		text = '(' + chr(letter_index) + ') ' + option_text
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		letter_index += 1
		
	x = SCREEN_WIDTH / 2 - width / 2
	y = SCREEN_HEIGHT /2 - height / 2
	#blit to root with slight background transparency (0.7 argument)
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
	
	#hang on player until a choice is made
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)
	
	#convert keypress to item index in inventory (or None) and return it
	index = key.c - ord('a')
	if index >= 0 and index < len(options): return index
	return None
	
##########################################
# msgbox(): display an important message, inna box
##########################################

def msgbox(text, width = 50):
	menu(text, [], width) #reuse menu because lazy is good programming
	
######################################
# inventory_menu(header): show player's inventory for various purposes, and allow picking an item from it
######################################

def inventory_menu(header):
	if len(inventory) == 0:
		options = ['Inventory is empty.']
	else:
		#indicate if an item is equipped equipment
		options = []
		for item in inventory:
			text = item.name
			if item.equipment and item.equipment.is_equipped:
				text = text + ' (on ' + item.equipment.slot + ')'
			options.append(text)
		
	index = menu(header, options, INVENTORY_WIDTH)
	
	if index is None or len(inventory) == 0:
		return None
	return inventory[index].item
	
#############
# Player input handling function
#############

def handle_keys():
	global key
	global player
	global fov_recompute
	global game_state
	
	player_action = False
	
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#Alt + Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'
	
	#movement keys
	#BUG note that this code counts movement keys as a turn even if you move into a wall or are similarly blocked
	if game_state == 'playing':
		#move keys in clockwise order, starting with up/north
		if (key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8):
			player_action = player_move_or_attack(0, -1)
		elif (key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9):
			player_action = player_move_or_attack(1, -1)
		elif (key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6):
			player_action = player_move_or_attack(1, 0)
		elif (key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3):
			player_action = player_move_or_attack(1, 1)
		elif (key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2):
			player_action = player_move_or_attack(0, 1)
		elif (key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1):
			player_action = player_move_or_attack(-1,1)
		elif (key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4):
			player_action = player_move_or_attack(-1, 0)
		elif (key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7):
			player_action = player_move_or_attack(-1, -1)
		elif key.vk == libtcod.KEY_KP5:
			player_action = True
		else:
			key_char = chr(key.c)
			
			#BUG these commands don't cost a turn at the moment
			# g - pick up an item if any are present
			if key_char == 'g':
				for object in objects:
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
						player_action = True
						break
			# i - view inventory and possibly use an item
			if key_char == 'i':
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other key to cancel.\n')
				if chosen_item is not None:
					chosen_item.use()
					player_action = True
			# c - view player's character screen
			if key_char == 'c':
				level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
				msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) + '\nExperience to level up: ' + str(level_up_xp) + '\nMaximum HP: ' + str(player.fighter.max_hp) + '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
			# d - view inventory and possibly drop an item
			if key_char == 'd':
				#show inventory, allow dropping an item
				chosen_item = inventory_menu('Press the key next to an item to drop it, or any other key to cancel.\n')
				if chosen_item is not None:
					chosen_item.drop()
					player_action = True
			# < - go down a level
			#not sure why tutorial represents down as '<'
			if key_char == '<':
				#go up(?) stairs
				if (stairs is not None) and stairs.x == player.x and stairs.y == player.y:
					next_level()
					
		if player_action == False:
			return 'didnt-take-turn'
			
#############################
# get_names_under_mouse(): get a string with the names of all objects under the mouse cursor
#############################

def get_names_under_mouse():
	global mouse
	
	(x, y) = (mouse.cx, mouse.cy)
	
	#get list of all objects' names in fov at mouse cursor's tile if tile is in fov
	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
		
	#reverse order so they're listed from most visible to least visible
	names = reversed(names)
	names = ', '.join(names)
	return names.capitalize()
	
#####################################
# target_tile(): get the player to click on a tile in range, and return that tile
#####################################

def target_tile(max_range= None):
	global key, mouse
	while True:
		#overdraw anything obscuring the map (e.g. the inventory UI)
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
		render_all()
		
		(x, y) = (mouse.cx, mouse.cy)
		
		if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and (max_range is None or player.distance(x, y) <= max_range)):
			return (x, y)
		#cancel on mouse2 or escape key
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			return (None, None)
			
################################
# target_monster(): get player to click a monster in fov and range, and returns it
################################

def target_monster(max_range=None):
	while True:
		(x, y) = target_tile(max_range)
		if x is None: #player cancelled
			return None
		
		#return only if a monster was clicked
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter and obj != player:
				return obj

#############################
# player_move_or_attack(dx, dy): contextually move or attack with PC
#############################

def player_move_or_attack(dx, dy):
	global fov_recompute
	
	moved_or_atook = False
	x = player.x + dx
	y = player.y + dy
	
	#check for attackable object
	target = None
	for object in objects:
		if object.fighter and object.x == x and object.y == y:
			target = object
			break
			
	if target is not None:
		player.fighter.attack(target)
		moved_or_atook = True
	elif player.move(dx, dy) == True:
		fov_recompute = True
		moved_or_atook = True
	
	return moved_or_atook
		
#####################################
# save_game(): saves current game state while playing
#####################################

def save_game():
	file = shelve.open('savegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['player_index'] = objects.index(player)
	file['inventory'] = inventory
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	if stairs is not None:
		file['stairs_index'] = objects.index(stairs)
	else:
		file['stairs_index'] = None
	file['dungeon_level'] = dungeon_level
	file.close()
	
#######################################
# load_game(): restores a previously saved game
#######################################

def load_game():
	global map, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level
	
	file = shelve.open('savegame', 'r')
	map = file['map']
	objects = file['objects']
	#index of player is important separate from player object, which is stored with the other objects
	player = objects[file['player_index']]
	inventory = file['inventory']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	stairs_index = file['stairs_index']
	if stairs_index is not None:
		stairs = objects[file['stairs_index']]
	else:
		stairs = None
	dungeon_level = file['dungeon_level']
	file.close()
	
	initialize_fov()

###############################
# new_game(): setup new game
###############################

def new_game():
	global player, inventory, game_msgs, game_state, dungeon_level
	
	inventory = []
	game_msgs = []
	game_state = 'playing'
	
	#make the player
	fighter_component = Fighter(hp = 50, defense = 1, power = 2, xp = 0, death_function = player_death)
	player = object(0, 0, '@', 'player', libtcod.white, move_blocker = True, fighter = fighter_component)
	player.level = 1
	
	#start with a dagger
	equipment_component = Equipment(slot='right hand', power_bonus=2)
	obj = object(0, 0, '-', 'dagger', libtcod.sky, always_visible = True, equipment = equipment_component)
	inventory.append(obj)
	equipment_component.equip()
	
	
	dungeon_level = 1
	make_map()
	#have to set up fov after making the map
	initialize_fov()

	#test message buffer and textwrap with long message
	message('Welcome, stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)
	
####################################
# initialize_fov(): make the player's fov_map usable
####################################

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True
	
	#Need to clear the console if playing 2+ games in one program session
	libtcod.console_clear(console)
	
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].sight_blocker, not map[x][y].move_blocker)

################################
# play_game(): loop through a game in progress
################################

def play_game():
	global key, mouse
	player_action = None
	
	mouse = libtcod.Mouse()
	key = libtcod.Key()
	
	while not libtcod.console_is_window_closed():
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()
		libtcod.console_flush()
		#check for player level up now, while objects are visible behind the menu
		check_level_up()
		#erase all objects after render in case they move before next flush
		for object in objects:
			object.clear()
		
		#handle player input and exit game if appropriate
		player_action = handle_keys()
		if player_action == 'exit':
			save_game()
			break

		#give monsters 1 turn for all player turns taken
		if game_state == 'playing' and player_action != 'didnt-take-turn':
			for object in objects:
				if object.ai:
					object.ai.take_turn()
			
#################################################
# main_menu(): Run at startup and give the player options to get playing
#################################################

def main_menu():
	img = libtcod.image_load('menu_background.png')
	
	
	while not libtcod.console_is_window_closed():
		#show the menu image in a terrible way
		libtcod.image_blit_2x(img, 0, 0, 0)
		
		#fancy main menu title and crediting
		libtcod.console_set_default_foreground(0, libtcod.white)
		libtcod.console_set_default_background(0, libtcod.black)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_ALPHA(0.7), libtcod.CENTER, 'JOTAF\'S COMPLETE ROGUELIKE TUTORIAL,')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-3, libtcod.BKGND_ALPHA(0.7), libtcod.CENTER, 'USING PYTHON+LIBTCOD')
		#libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_ALPHA(0.7), libtcod.CENTER, 'Implemented By')
		
		#show main menu optionss and request selection
		choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
		
		#fullscreen toggle needs to work in main menu too
		#if key.vk == libtcod.KEY_ENTER and key.lalt:
		#	libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
		
		if choice == 0: #new game
			new_game()
			play_game()
		elif choice == 1: #load game
			try:
				load_game()
			except:
				msgbox('\n No saved game to load.\n', 24)
				continue
			play_game()
		elif choice == 2: #quit
			break
		
#############
# System Initialization
#############

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Roguebasin Python Roguelike', False)
libtcod.sys_set_fps(LIMIT_FPS)

#draw all map graphics on this and then blit to root
console = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
#gui panel (also blitted to root)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

main_menu()
