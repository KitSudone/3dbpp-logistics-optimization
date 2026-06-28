# File: sa_algorithm.py
import copy
import random
import math
from core_objects import Item, Bin
from ffd_algorithm import can_fit, run_ffd

def pack_sequence(bin_obj, item_sequence):
    """Mengepak barang berdasarkan urutan array yang dilempar SA"""
    bin_obj.fitted_items = []
    for item in item_sequence:
        item.x, item.y, item.z = None, None, None
        
    available_points = [(0, 0, 0)]
    
    for item in item_sequence:
        placed = False
        # PERBAIKAN SORTING: Utamakan p (Z) agar selalu jatuh ke lantai terendah
        available_points.sort(key=lambda p: (p, p, p))
        
        for point in available_points:
            x, y, z = point
            if can_fit(bin_obj, item, x, y, z):
                item.x, item.y, item.z = x, y, z
                bin_obj.fitted_items.append(item)
                placed = True
                
                available_points.remove(point)
                available_points.append((x + item.length, y, z))
                available_points.append((x, y + item.width, z))
                available_points.append((x, y, z + item.height))
                break
                
    return bin_obj

def mutate(item_sequence):
    new_sequence = copy.deepcopy(item_sequence)
    mutation_type = random.choice(["rotation", "swap"])
    
    if mutation_type == "rotation":
        item = random.choice(new_sequence)
        dimensi = [item.length, item.width, item.height]
        random.shuffle(dimensi)
        item.length, item.width, item.height = dimensi
        
    elif mutation_type == "swap":
        priorities = list(set([i.route_priority for i in new_sequence]))
        chosen_priority = random.choice(priorities)
        indices = [i for i, item in enumerate(new_sequence) if item.route_priority == chosen_priority]
        
        if len(indices) >= 2:
            idx1, idx2 = random.sample(indices, 2)
            new_sequence[idx1], new_sequence[idx2] = new_sequence[idx2], new_sequence[idx1]
            
    return new_sequence

def get_compactness_score(bin_obj):
    if not bin_obj.fitted_items: return 0
    max_x = max(i.x + i.length for i in bin_obj.fitted_items)
    max_y = max(i.y + i.width for i in bin_obj.fitted_items)
    max_z = max(i.z + i.height for i in bin_obj.fitted_items)
    return -(max_x * max_y * max_z) / 1000

def run_sa(bin_obj, initial_sequence, T0=100, alpha=0.95, Tmin=1):

    def hitung_energi(b):
        """Energi = utamakan jumlah barang muat, lalu kompaksi"""
        if not b.fitted_items:
            return -float('inf')
        return len(b.fitted_items) * 10000 + get_compactness_score(b)

    current_sequence = copy.deepcopy(initial_sequence)
    test_bin = Bin(bin_obj.length, bin_obj.width, bin_obj.height)
    pack_sequence(test_bin, current_sequence)
    current_energy = hitung_energi(test_bin)

    best_sequence = copy.deepcopy(current_sequence)
    best_energy   = current_energy

    T = T0

    while T > Tmin:
        new_sequence = mutate(current_sequence)
        new_bin      = Bin(bin_obj.length, bin_obj.width, bin_obj.height)
        pack_sequence(new_bin, new_sequence)
        new_energy = hitung_energi(new_bin)

        delta_e = new_energy - current_energy

        if delta_e >= 0 or random.random() < math.exp(delta_e / T):
            current_sequence = new_sequence
            current_energy   = new_energy

            if current_energy > best_energy:
                best_sequence = copy.deepcopy(current_sequence)
                best_energy   = current_energy

        T *= alpha

    final_bin = Bin(bin_obj.length, bin_obj.width, bin_obj.height)
    pack_sequence(final_bin, best_sequence)
    return final_bin