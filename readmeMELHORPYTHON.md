import customtkinter as ctk
from skyfield.api import Loader, Topos
import serial
import time
import threading
from datetime import timedelta

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class TelescopeControl(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.tracking_active = False  # Novo estado de rastreamento
        self.current_astro = None     # Astro sendo rastreado
        # self.calibrated = False
        self.title("Controle do Telescópio Espacial 🌌")
        self.geometry("1000x800")
        self.serial_connection = None
        self.serial_thread = None  # Thread para leitura da serial
        self.selected_astro = None
        self.last_correction_time = time.time()
        self.astros = []
        self.zero_position = (0, 0)
        self.azimuth_offset = 21.0  # Ajuste manual de 21° no início
        
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

            self.main_frame = ctk.CTkFrame(self, corner_radius=10)
            self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
            self.main_frame.grid_columnconfigure(0, weight=1)

            self.location_frame = ctk.CTkFrame(self.main_frame)
            self.location_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

            self.connection_frame = ctk.CTkFrame(self.main_frame)
            self.connection_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
            
            self.btn_connect = ctk.CTkButton(self.connection_frame, text="🔌 Conectar Arduino", command=self.connect_arduino)
            self.btn_connect.pack(side="left", padx=10, pady=5)
            
            self.connection_status = ctk.CTkLabel(self.connection_frame, text="⭕ Desconectado", text_color="red")
            self.connection_status.pack(side="left", padx=10)
            
            # Crie o frame de controle antes de usá-lo
            self.control_frame = ctk.CTkFrame(self.main_frame)
            self.control_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
            
            # Botão de rastreamento contínuo (novo)
            self.btn_track = ctk.CTkButton(
                self.control_frame, 
                text="🔄 Iniciar Rastreamento", 
                command=self.toggle_tracking,
                state="disabled",
                fg_color="#00AA00",
                hover_color="#008800"
            )
            self.btn_track.pack(side="left", padx=5)
            
            self.btn_stop = ctk.CTkButton(self.control_frame, text="⏹ Interromper Rastreamento", command=self.stop_tracking, fg_color="#FF0000", hover_color="#CC0000")
            self.btn_stop.pack(side="left", padx=5)

            # Novo label de status de rastreamento
            self.tracking_status = ctk.CTkLabel(self.main_frame, text="Status: Não está rastreando", font=("Arial", 12))
            self.tracking_status.grid(row=6, column=0, padx=10, pady=5)

            # self.btn_calibrate = ctk.CTkButton(
            #     self.main_frame, 
            #     text="🧭 Calibrar Posição Inicial", 
            #     command=self.calibrate_north, 
            #     fg_color="blue", 
            #     hover_color="darkblue"
            # )
            # self.btn_calibrate.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

            self.astros_list = ctk.CTkScrollableFrame(self.main_frame, height=200)
            self.astros_list.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
            self.astro_buttons = []

            self.info_frame = ctk.CTkFrame(self.main_frame)
            self.info_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
            
            self.lbl_altitude = ctk.CTkLabel(self.info_frame, text="Altitude: --", font=("Arial", 14))
            self.lbl_altitude.pack(side="left", padx=20, pady=10)
            
            self.lbl_azimute = ctk.CTkLabel(self.info_frame, text="Azimute: --", font=("Arial", 14))
            self.lbl_azimute.pack(side="left", padx=20, pady=10)


    # Novo método para alternar o rastreamento
    def toggle_tracking(self):
        self.tracking_active = not self.tracking_active
        if self.tracking_active:
            self.btn_track.configure(text="⏸ Pausar Rastreamento", fg_color="#AA0000", hover_color="#880000")
            self.tracking_status.configure(text=f"Status: Rastreando {self.current_astro}", text_color="green")
        else:
            self.btn_track.configure(text="🔄 Retomar Rastreamento", fg_color="#00AA00", hover_color="#008800")
            self.tracking_status.configure(text="Status: Rastreamento pausado", text_color="orange")
            
    # def calibrate_north(self):
    #     """Comando para alinhar a base ao Norte Geográfico e altitude ao horizonte"""
    #     if self.serial_connection and self.serial_connection.is_open:
    #         try:
    #             # Envia o comando para girar a base em 21° para leste
    #             comando_azimute = "CALIBRATE_NORTH,21.0\n"
    #             self.serial_connection.write(comando_azimute.encode('utf-8'))
    #             time.sleep(5)  # Pausa para garantir o movimento
                
    #             # Envia o comando para zerar a altitude
    #             comando_altitude = "CALIBRATE_ALTITUDE,0.0\n"
    #             self.serial_connection.write(comando_altitude.encode('utf-8'))
                
    #             # Atualiza status e libera os botões dos astros
    #             self.calibrated = True
    #             self.connection_status.configure(text="✅ Norte e Altitude Calibrados!", text_color="blue")
    #             print("[PYTHON] Comandos de calibração enviados: Norte e Altitude")
                
    #             # Atualiza os botões dos astros para ficarem habilitados
    #             self.update_astro_buttons()
            
    #         except Exception as e:
    #             self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")


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
                hover_color="#3D3F41",
                state="normal" 
            )
            btn.pack(fill="x", pady=2)
            self.astro_buttons.append(btn)



    def stop_tracking(self):
        self.tracking_active = False
        self.current_astro = None
        self.btn_track.configure(state="disabled")
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"STOP\n")
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")
        self.selected_astro = None
        self.lbl_altitude.configure(text="Altitude: --")
        self.lbl_azimute.configure(text="Azimute: --")
        self.connection_status.configure(text="✅ Rastreamento Interrompido", text_color="orange")

    def get_astro_data(self):
        loader = Loader('~/skyfield-data')
        planets = loader('de421.bsp')
        ts = loader.timescale()
    
        # Coordenadas fixas de Formosa-GO
        latitude_observador = -15.541232599693457  # Negativo para Sul, 
        longitude_observador = -47.33334646343277  # Negativo para Oeste
    
        observador = planets['earth'] + Topos(
            latitude_degrees=latitude_observador,
            longitude_degrees=longitude_observador
        )
    
        astros = {}
        agora = ts.now()
        futuro = ts.from_datetime(agora.utc_datetime() + timedelta(seconds=10))

        for nome, corpo in [
            ('Lua', planets['moon']),
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

    def connect_arduino(self):
        try:
            portas = ['COM3', 'COM4', 'COM5', 'COM6', '/dev/ttyUSB0', '/dev/ttyACM0']
            for porta in portas:
                try:
                    self.serial_connection = serial.Serial(
                        porta,
                        baudrate=115200,
                        timeout=1,
                        write_timeout=1
                    )
                    time.sleep(2)
                    self.connection_status.configure(text=f"✅ Conectado em {porta}", text_color="green")
                    # Inicia a thread para ler a saída do Arduino
                    if self.serial_thread is None:
                        self.serial_thread = threading.Thread(target=self.read_from_serial, daemon=True)
                        self.serial_thread.start()
                    return
                except Exception:
                    continue
            raise Exception("Nenhuma porta encontrada!")
        except Exception as e:
            self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")

    def read_from_serial(self):
        """Thread que lê continuamente a saída do Arduino e imprime no console."""
        while True:
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        print(f"[ARDUINO OUTPUT] {line}")
            except Exception as e:
                print(f"Erro ao ler da serial: {e}")
            time.sleep(0.1)

    def send_velocity_command(self, vel_alt, vel_azi):
        if self.serial_connection:
            try:
                # Aumenta a velocidade multiplicando os valores por um fator.
                fator = 10  # Ajuste este valor conforme necessário.
                # Limita a velocidade para ±10°/s após o aumento
                safe_vel_alt = max(min(vel_alt * fator, 10.0), -10.0)
                safe_vel_azi = max(min(vel_azi * fator, 10.0), -10.0)
                comando = f"SPEED,{safe_vel_alt:.6f},{safe_vel_azi:.6f}\n"
                self.serial_connection.write(comando.encode('utf-8'))
                print(f"[PYTHON] Comando SPEED enviado: {comando.strip()}")
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")


    def send_position_command(self, alt, azi):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                adjusted_azi = azi + self.azimuth_offset
                if adjusted_azi >= 360:
                    adjusted_azi -= 360
                
                if not (-90 <= alt <= 90) or not (0 <= adjusted_azi <= 360):
                    print("Coordenadas inválidas!")
                    return
                
                comando = f"POS,{alt:.2f},{adjusted_azi:.2f}\n"
                self.serial_connection.write(comando.encode('utf-8'))
                print(f"[PYTHON] Comando POS enviado: {comando.strip()}")
                time.sleep(10)  # Aguarda o movimento ser concluído
            except Exception as e:
                print(f"Erro crítico ao enviar POS: {str(e)}")


    def select_astro(self, astro):
        self.current_astro = astro['nome']
        self.selected_astro = astro['nome']
        
        print(f"\n[DEBUG] Movendo para {astro['nome']}:")
        print(f"Altitude: {astro['altitude']:.2f}°")
        print(f"Azimute: {astro['azimute']:.2f}°")
        
        # Atualiza a interface
        self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
        self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")
        self.btn_track.configure(state="normal")  # Habilita o botão de rastreamento
        
        # Envia apenas o posicionamento inicial
        self.send_position_command(astro['altitude'], astro['azimute'])
        
        # Se já estava rastreando, mantém o estado
        if self.tracking_active:
            self.toggle_tracking()

    def update_data(self):
        if self.tracking_active and self.current_astro:
            try:
                # Atualiza as coordenadas do astro
                self.astros = self.get_astro_data()
                astro = next(a for a in self.astros if a['nome'] == self.current_astro)

                # Calcula a velocidade necessária para rastrear o astro
                vel_azi = astro['vel_azi']  # Velocidade em graus/segundo
                vel_alt = astro['vel_alt']  # Velocidade em graus/segundo

                # Limita as velocidades a valores realistas
                vel_azi = max(min(vel_azi, 0.01), -0.01)  # Exemplo: +/- 0.01 graus/segundo
                vel_alt = max(min(vel_alt, 0.01), -0.01)

                # Envia o comando SPEED para ambos azimute e altitude
                self.send_velocity_command(vel_alt, vel_azi)

                # Atualiza a interface
                self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
                self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")

            except StopIteration:
                self.tracking_status.configure(text="Erro: Astro não encontrado!", text_color="red")
                self.toggle_tracking()

        self.after(1000, self.update_data)



if __name__ == "__main__":
    app = TelescopeControl()
    app.mainloop()

