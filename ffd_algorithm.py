# File: ffd_algorithm.py
from core_objects import Item, Bin

def is_overlapping(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
    """Mengecek apakah dua balok saling bertabrakan"""
    if (x1 >= x2 + l2 or x2 >= x1 + l1): return False 
    if (y1 >= y2 + w2 or y2 >= y1 + w1): return False 
    if (z1 >= z2 + h2 or z2 >= z1 + h1): return False 
    return True 

def has_support(x, y, z, l, w, placed_items, threshold=1.0):
    """
    LOGIKA GRAVITASI KETAT: 
    threshold=1.0 berarti 100% alas barang harus menapak (di lantai atau di atas barang lain).
    """
    if z == 0:
        return True # Menapak sempurna di lantai bak
    
    total_supported_area = 0
    item_area = l * w
    
    for p_item in placed_items:
        # Cek barang yang tepat berada di bawah (selisih Z sangat kecil/nol)
        if abs((p_item.z + p_item.height) - z) < 0.01:
            overlap_x = max(0, min(x + l, p_item.x + p_item.length) - max(x, p_item.x))
            overlap_y = max(0, min(y + w, p_item.y + p_item.width) - max(y, p_item.y))
            total_supported_area += (overlap_x * overlap_y)
            
    # Menggunakan toleransi kecil (0.99) untuk menghindari error pembulatan float
    return (total_supported_area / item_area) >= 0.99

def can_fit(bin_obj, item, x, y, z):
    """Validasi posisi penempatan barang"""
    if x + item.length > bin_obj.length: return False
    if y + item.width > bin_obj.width: return False
    if z + item.height > bin_obj.height: return False

    if not has_support(x, y, z, item.length, item.width, bin_obj.fitted_items):
        return False

    for placed_item in bin_obj.fitted_items:
        if is_overlapping(x, y, z, item.length, item.width, item.height,
                          placed_item.x, placed_item.y, placed_item.z,
                          placed_item.length, placed_item.width, placed_item.height):
            return False
    return True

def run_ffd(bin_obj, list_items):
    """Algoritma FFD dengan Prioritas Lantai (Floor-First)"""
    # Urutkan barang berdasarkan rute (LIFO) dan volume
    sorted_items = sorted(list_items, key=lambda i: (i.route_priority, -i.get_volume()))
    
    # Titik awal selalu dari pojok lantai
    available_points = [(0, 0, 0)]
    
    for item in sorted_items:
        # PENTING: Urutkan titik agar sumbu Z (Tinggi) 
        # menjadi prioritas paling utama (paling rendah dulu)
        # Kemudian sumbu X (Panjang) dan Y (Lebar)
        available_points.sort(key=lambda p: (p, p, p))
        
        placed = False
        for point in available_points:
            x, y, z = point
            if can_fit(bin_obj, item, x, y, z):
                item.x, item.y, item.z = x, y, z
                bin_obj.fitted_items.append(item)
                placed = True
                
                # Tambahkan titik baru yang tercipta setelah barang ditaruh
                available_points.remove(point)
                
                # Titik baru di sebelah kanan, depan, dan atas barang
                new_points = [
                    (x + item.length, y, z),
                    (x, y + item.width, z),
                    (x, y, z + item.height)
                ]
                
                for np in new_points:
                    # Hanya tambahkan titik jika belum ada di daftar
                    if np not in available_points:
                        available_points.append(np)
                break
    return bin_obj