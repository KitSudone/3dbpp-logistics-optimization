# File: core_objects.py

class Item:
    """
    Class ini adalah cetakan untuk merepresentasikan 1 unit barang/bal kemasan.
    """
    def __init__(self, item_id, length, width, height, route_priority):
        self.item_id = item_id
        
        # Dimensi asli
        self.length = length
        self.width = width
        self.height = height
        
        # Prioritas LIFO (Semakin kecil angkanya, semakin terakhir dikeluarkan)
        # Contoh: Toko B (Terjauh) = Prioritas 1. Toko A (Terdekat) = Prioritas 2.
        self.route_priority = route_priority
        
        # Orientasi / Rotasi (0 sampai 5, sesuai jurnal 3D-BPP)
        # Default = 0 (Tidak diputar)
        self.rotation_type = 0 
        
        # Koordinat penempatan (x, y, z). None berarti belum dimasukkan ke armada.
        self.x = None
        self.y = None
        self.z = None

    def get_volume(self):
        # Menghitung volume barang untuk algoritma Decreasing (pengurutan)
        return self.length * self.width * self.height
    
    def __repr__(self):
        # Format agar saat di-print di terminal tampilannya rapi
        return f"Item({self.item_id}, Rute:{self.route_priority}, Vol:{self.get_volume()})"


class Bin:
    """
    Class ini adalah cetakan untuk merepresentasikan Armada (Suzuki Carry).
    """
    def __init__(self, length, width, height):
        self.length = length
        self.width = width
        self.height = height
        
        # Daftar barang yang sudah berhasil dimasukkan ke dalam armada ini
        self.fitted_items = []
        
    def get_total_volume(self):
        # Kapasitas total armada
        return self.length * self.width * self.height
    
    def get_used_volume(self):
        # Menghitung volume yang sudah terpakai
        used = sum(item.get_volume() for item in self.fitted_items)
        return used
        
    def get_fill_rate(self):
        # Menghitung efisiensi (Persentase Keterisian)
        if self.get_total_volume() == 0:
            return 0
        return (self.get_used_volume() / self.get_total_volume()) * 100
        
    def __repr__(self):
        return f"Armada(Isi: {len(self.fitted_items)} barang, Fill Rate: {self.get_fill_rate():.2f}%)"

# --- BAGIAN UNTUK TESTING ---
# Kode di bawah ini hanya berjalan jika Anda mengeksekusi file ini langsung
if __name__ == "__main__":
    print("--- Menguji Cetakan Tahap 2 ---")
    
    # 1. Membuat cetakan armada Suzuki Carry (220 x 148 x 30 cm)
    carry = Bin(220, 148, 80)
    print("Armada dibuat:", carry)
    
    # 2. Membuat beberapa barang contoh
    barang1 = Item("B-008", 100, 36, 24, route_priority=1) # Toko B
    barang2 = Item("B-001", 69, 46, 24, route_priority=2)  # Toko A
    
    print("Barang 1:", barang1)
    print("Barang 2:", barang2)