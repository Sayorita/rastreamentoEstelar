import customtkinter as ctk
from skyfield.api import Star, load, Topos
import serial
import geocoder
import time
from datetime import timedelta 
from geomagpy.mag import GeoMag
from skyfield.data import hipparcos




ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class TelescopeControl(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Controle do Telescópio Espacial 🌌")
        self.geometry("1000x800")
        self.serial_connection = None
        self.selected_astro = None
        self.last_correction_time = time.time()
        self.observador_location = (-15.7942, -47.8822)
        self.astros = []  # Inicialização correta
        
        self.create_widgets()
        self.astros = self.get_astro_data()
        self.update_astro_buttons()
        
        self.after(1000, self.update_data)

    def update_astro_buttons(self):
        for btn in self.astro_buttons:
            btn.destroy()
        self.astro_buttons = []
        
        for astro in self.astros:
            btn = ctk.CTkButton(
                self.astros_list,
                text=f"{astro['nome']} 🌟",
                command=lambda a=astro: self.select_astro(a),
                corner_radius=8,
                fg_color="#2A2D2E",
                hover_color="#3D3F41"
            )
            btn.pack(fill="x", pady=2)
            self.astro_buttons.append(btn)
    
    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Seção de localização
        self.location_frame = ctk.CTkFrame(self.main_frame)
        self.location_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.btn_get_location = ctk.CTkButton(
            self.location_frame,
            text="📍 Obter Localização Automática",
            command=self.get_observador_location
        )
        self.btn_get_location.pack(side="left", padx=5)
        
        self.lbl_location = ctk.CTkLabel(
            self.location_frame,
            text=f"Lat/Lon: {self.observador_location[0]:.4f}, {self.observador_location[1]:.4f}",
            font=("Arial", 12)
        )
        self.lbl_location.pack(side="left", padx=10)
        # Adicione isso no create_widgets(), após o lbl_location
        self.lbl_declinacao = ctk.CTkLabel(
            self.location_frame,
            text="Declinação: --",
            font=("Arial", 12),
            text_color="#00FF00"
            )
        self.lbl_declinacao.pack(side="left", padx=10)

        # Seção de conexão Arduino
        self.connection_frame = ctk.CTkFrame(self.main_frame)
        self.connection_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.btn_connect = ctk.CTkButton(
            self.connection_frame,
            text="🔌 Conectar Arduino",
            command=self.connect_arduino
        )
        self.btn_connect.pack(side="left", padx=10, pady=5)
        
        self.connection_status = ctk.CTkLabel(
            self.connection_frame,
            text="⭕ Desconectado",
            text_color="red"
        )
        self.connection_status.pack(side="left", padx=10)

        # Lista de astros
        self.astros_list = ctk.CTkScrollableFrame(self.main_frame, height=200)
        self.astros_list.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        self.astro_buttons = []
        for astro in self.astros:
            btn = ctk.CTkButton(
                self.astros_list,
                text=f"{astro['nome']} 🌟",
                command=lambda a=astro: self.select_astro(a),
                corner_radius=8,
                fg_color="#2A2D2E",
                hover_color="#3D3F41"
            )
            btn.pack(fill="x", pady=2)
            self.astro_buttons.append(btn)

        # Painel de informações
        self.info_frame = ctk.CTkFrame(self.main_frame)
        self.info_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.lbl_altitude = ctk.CTkLabel(
            self.info_frame,
            text="Altitude: --",
            font=("Arial", 14)
        )
        self.lbl_altitude.pack(side="left", padx=20, pady=10)
        
        self.lbl_azimute = ctk.CTkLabel(
            self.info_frame,
            text="Azimute: --",
            font=("Arial", 14)
        )
        self.lbl_azimute.pack(side="left", padx=20, pady=10)

        # Controles manuais
        self.manual_frame = ctk.CTkFrame(self.main_frame)
        self.manual_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        
        self.entry_lat = ctk.CTkEntry(self.manual_frame, placeholder_text="Latitude", width=120)
        self.entry_lat.pack(side="left", padx=5)
        
        self.entry_lon = ctk.CTkEntry(self.manual_frame, placeholder_text="Longitude", width=120)
        self.entry_lon.pack(side="left", padx=5)
        
        self.btn_set_location = ctk.CTkButton(
            self.manual_frame,
            text="Definir Localização Manual",
            command=self.set_manual_location
        )
        self.btn_set_location.pack(side="left", padx=5)

    def get_observador_location(self):
        try:
            g = geocoder.ip('me')
            if g.latlng:
                self.observador_location = (g.latlng[0], g.latlng[1])
            
            # Cálculo da declinação magnética (mantido)
            wmm = WorldMagneticModel()
            declination = wmm.calculate(g.latlng[0], g.latlng[1]).declination
            
            # Novo: Cálculo do Norte Geográfico via estrelas
            load = Loader('~/skyfield-data')
            ts = load.timescale()
            planets = load('de421.bsp')
            
            # Carrega catálogo de estrelas
            with load.open(hipparcos.URL) as f:
                df = hipparcos.load_dataframe(f)
            
            observador = planets['earth'] + Topos(
                latitude_degrees=self.observador_location[0],
                longitude_degrees=self.observador_location[1]
            )
            
            # Escolhe a estrela de referência conforme o hemisfério
            if self.observador_location[0] >= 0:  # Hemisfério Norte
                polaris = Star.from_dataframe(df.loc[11767])  # HIP 11767 = Polaris
                corpo_ref = polaris
            else:  # Hemisfério Sul
                acrux = Star.from_dataframe(df.loc[60718])  # HIP 60718 = Alpha Crucis (Cruzeiro do Sul)
                corpo_ref = acrux
            
            # Calcula a posição da estrela
            t = ts.now()
            astrometric = observador.at(t).observe(corpo_ref)
            alt, az, _ = astrometric.apparent().altaz()
            
            # Determina o Norte Geográfico
            if self.observador_location[0] >= 0:
                norte_geografico = az.degrees  # Polaris aponta diretamente para o Norte
            else:
                sul_celeste = (az.degrees + 180) % 360  # Cruzeiro do Sul aponta para o Sul
                norte_geografico = (sul_celeste + 180) % 360
            
            # Atualiza a interface
            self.lbl_declinacao.configure(
                text=f"Declinação: {declination:.2f}° | Norte Verdadeiro: {norte_geografico:.2f}°"
            )
            
            self.astros = self.get_astro_data()
            
        except Exception as e:
            self.lbl_location.configure(text=f"Erro: {str(e)}", text_color="red")


    def set_manual_location(self):
        try:
            lat = float(self.entry_lat.get())
            lon = float(self.entry_lon.get())
            self.observador_location = (lat, lon)
            self.lbl_location.configure(text=f"Lat/Lon: {lat:.4f}, {lon:.4f}")
            self.astros = self.get_astro_data()
        except ValueError:
            self.lbl_location.configure(text="Valores inválidos!", text_color="red")

    from datetime import timedelta  # Adicione esta importação no início do arquivo

    def get_astro_data(self):
        planets = load('de421.bsp')
        ts = load.timescale()
        observador = planets['earth'] + Topos(
            latitude_degrees=self.observador_location[0],
            longitude_degrees=self.observador_location[1]
        )
        
        astros = {}
        agora = ts.now()
        futuro = ts.from_datetime(agora.utc_datetime() + timedelta(seconds=10))  # Correção aqui

        for nome, corpo in [
            ('Lua', planets['moon']),
            ('Júpiter', planets['jupiter barycenter']),
            ('Saturno', planets['saturn barycenter'])
        ]:
            pos_atual = (corpo - observador).at(agora).altaz()
            pos_futura = (corpo - observador).at(futuro).altaz()
            
            astros[nome] = {
                'nome': nome,
                'altitude': pos_atual[0].degrees,
                'azimute': pos_atual[1].degrees,
                'vel_alt': (pos_futura[0].degrees - pos_atual[0].degrees) / 10,
                'vel_azi': (pos_futura[1].degrees - pos_atual[1].degrees) / 10
            }

        return list(astros.values())

    def connect_arduino(self):  # Método adicionado
        try:
            self.serial_connection = serial.Serial('COM3', 9600, timeout=1)
            self.connection_status.configure(text="✅ Conectado", text_color="green")
        except Exception as e:
            self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")

    def select_astro(self, astro):
        self.selected_astro = astro['nome']
        self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
        self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")
        self.send_velocity_command(astro['vel_alt'], astro['vel_azi'])

    def send_velocity_command(self, vel_alt, vel_azi):
        if self.serial_connection:
            try:
                comando = f"SPEED,{vel_alt:.6f},{vel_azi:.6f}\n"
                self.serial_connection.write(comando.encode())
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")

    def update_data(self):
        if self.selected_astro in ['Lua', 'Saturno']:
            self.astros = self.get_astro_data()
            astro = next(a for a in self.astros if a['nome'] == self.selected_astro)
            
            if time.time() - self.last_correction_time > 5:
                self.send_position_command(astro['altitude'], astro['azimute'])
                self.last_correction_time = time.time()

        self.after(1000, self.update_data)

    def send_position_command(self, alt, azi):
        if self.serial_connection:
            try:
                comando = f"POS,{alt:.6f},{azi:.6f}\n"
                self.serial_connection.write(comando.encode())
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")

if __name__ == "__main__":
    app = TelescopeControl()
    app.mainloop()