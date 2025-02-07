import customtkinter as ctk
from skyfield.api import Loader, Topos
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import serial
import time
import threading
from datetime import timedelta

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Classe para exibir o gráfico do céu
class SkyPlotFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.figure = plt.Figure(figsize=(6,6), dpi=100)
        self.ax = self.figure.add_subplot(111, projection='polar')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
       
        self.plot_sky()
        

    def plot_sky(self):
        # Carrega dados efemérides do Skyfield
        load = Loader('~/skyfield-data')
        planets = load('de421.bsp')
        ts = load.timescale()

        # Define a localização do observador (Exemplo: Formosa-GO)
        latitude_observador = -15.541232599693457  # em graus
        longitude_observador = -47.33334646343277   # em graus
        observador = planets['earth'] + Topos(latitude_degrees=latitude_observador,
                                              longitude_degrees=longitude_observador)
        # Define o instante da observação
        t = ts.now()

        # Calcula a posição da Lua e de Saturno
        altaz_lua = (planets['moon'] - observador).at(t).altaz()
        altaz_saturno = (planets['saturn barycenter'] - observador).at(t).altaz()

        alt_lua, az_lua = altaz_lua[0].degrees, altaz_lua[1].degrees
        alt_saturno, az_saturno = altaz_saturno[0].degrees, altaz_saturno[1].degrees

        # Converter para coordenadas polares:
        # Theta: azimute convertido para radianos
        # r: 90 - altitude, de forma que o zênite (90°) fique no centro (r=0) e o horizonte (0°) no limite (r=90)
        theta_lua = np.deg2rad(az_lua)
        r_lua = 90 - alt_lua

        theta_saturno = np.deg2rad(az_saturno)
        r_saturno = 90 - alt_saturno

        # Limpar o gráfico (caso seja chamado novamente)
        self.ax.clear()

        # Configurar o gráfico polar
        self.ax.set_theta_zero_location("N")  # 0° no topo (Norte)
        self.ax.set_theta_direction(-1)       # Ângulos crescem no sentido horário

        # Plota o círculo que representa o horizonte (r = 90°)
        theta = np.linspace(0, 2*np.pi, 100)
        self.ax.plot(theta, np.full_like(theta, 90), color='gray', linestyle='--')

        # Plota as posições dos astros
        self.ax.scatter(theta_lua, r_lua, color='blue', s=100, label='Lua')
        self.ax.scatter(theta_saturno, r_saturno, color='red', s=100, label='Saturno')

        # Configurações adicionais do gráfico
        self.ax.set_rmax(90)
        self.ax.set_rticks([0, 30, 60, 90])
        self.ax.set_rlabel_position(170)
        self.ax.legend(loc='upper right')

        # Atualiza o canvas
        self.canvas.draw()

class TelescopeControl(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.tracking_active = False  # Novo estado de rastreamento
        self.current_astro = None     # Astro sendo rastreado
        self.calibrated = False
        self.title("Controle do Telescópio Espacial 🌌")
        self.geometry("1000x800")
        self.serial_connection = None
        self.serial_thread = None  # Thread para leitura da serial
        self.selected_astro = None
        self.last_correction_time = time.time()
        self.moving_to_position = False  # Flag para movimento POS
        self.astros = []
        self.zero_position = (0, 0)
        self.azimuth_offset = 21.0  # Ajuste manual de 21° no início
        
        self.create_widgets()
        
        self.astros = self.get_astro_data()
        self.update_astro_buttons()
        
        self.after(1000, self.update_data)
    
    def create_widgets(self):
        COLOR_BACKGROUND = "#000000"  # preto
        COLOR_HIGHLIGHT = "#092E6E"   # azul normal
        COLOR_SUCCESS = "#32CD32"     # Verde limão
        COLOR_WARNING = "#ADCBFF"     # Laranja
        COLOR_ERROR = "#FF4500"       # Vermelho laranja
        COLOR_TEXT_MAIN = "#FFFFFF"   # Branco
        COLOR_TEXT_SECONDARY = "#A9A9A9"  # Cinza claro

        # Configura o grid do widget principal (this widget)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Cria o main_frame que contém todo o conteúdo e o divide em duas colunas
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=COLOR_BACKGROUND)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0)  # Título
        self.main_frame.grid_rowconfigure(1, weight=1)  # Conteúdo principal
        self.main_frame.grid_rowconfigure(2, weight=0)  # Botão "Visualizar Mapa Celeste"

        # Título de localização, ocupando as duas colunas
        self.localizacao = ctk.CTkLabel(self.main_frame, text="Localização: Formosa-GO", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_MAIN)
        self.localizacao.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # -----------------------------
        # Coluna ESQUERDA: Conectar, lista de astros e rastreamento
        # -----------------------------
        self.left_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BACKGROUND)
        self.left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Frame de conexão com o Arduino
        self.connection_frame = ctk.CTkFrame(self.left_frame, fg_color=COLOR_BACKGROUND)
        self.connection_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.btn_connect = ctk.CTkButton(self.connection_frame, text="🔌 Conectar Arduino", command=self.connect_arduino, corner_radius=20, fg_color=COLOR_HIGHLIGHT, text_color=COLOR_TEXT_MAIN, hover_color="#1E90FF")
        self.btn_connect.pack(side="left", padx=10, pady=5)
        self.connection_status = ctk.CTkLabel(self.connection_frame, text="⭕ Desconectado", text_color=COLOR_ERROR)
        self.connection_status.pack(side="left", padx=10)

        # Lista de astros
        self.astros_list = ctk.CTkScrollableFrame(self.left_frame, height=200, fg_color=COLOR_BACKGROUND)
        self.astros_list.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.astro_buttons = []

        # Frame para controles de rastreamento (iniciar/pausar)
        self.track_frame = ctk.CTkFrame(self.left_frame, fg_color=COLOR_BACKGROUND)
        self.track_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.btn_track = ctk.CTkButton(
            self.track_frame, 
            text="🔄 Iniciar Rastreamento", 
            command=self.toggle_tracking,
            state="disabled",  # Inicialmente desabilitado
            fg_color=COLOR_SUCCESS,
            hover_color="#228B22",
            corner_radius=20,
            text_color=COLOR_TEXT_MAIN
        )
        self.btn_track.pack(side="left", padx=5)
        self.btn_stop = ctk.CTkButton(
            self.track_frame, 
            text="⏹ Interromper Rastreamento", 
            command=self.stop_tracking, 
            state="disabled",  # Inicialmente desabilitado
            fg_color=COLOR_ERROR, 
            hover_color="#CC0000",
            corner_radius=20,
            text_color=COLOR_TEXT_MAIN
        )
        self.btn_stop.pack(side="right", padx=5)

        # Informações adicionais (ex: altitude e azimute)
        self.info_frame = ctk.CTkFrame(self.left_frame, fg_color=COLOR_BACKGROUND)
        self.info_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.lbl_altitude = ctk.CTkLabel(self.info_frame, text="Altitude: --", font=("Arial", 14), text_color=COLOR_TEXT_MAIN)
        self.lbl_altitude.pack(side="left", padx=20, pady=10)
        self.lbl_azimute = ctk.CTkLabel(self.info_frame, text="Azimute: --", font=("Arial", 14), text_color=COLOR_TEXT_MAIN)
        self.lbl_azimute.pack(side="left", padx=20, pady=10)

        # Tracking status (opcional)
        self.tracking_status = ctk.CTkLabel(self.left_frame, text="Status: Não está rastreando", font=("Arial", 12), corner_radius=20, text_color=COLOR_TEXT_SECONDARY)
        self.tracking_status.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        # -----------------------------
        # Coluna DIREITA: Botão de calibrar e controles de movimento (setinhas maiores)
        # -----------------------------
        self.right_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BACKGROUND)
        self.right_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Botão de calibrar telescópio
        self.btn_calibrate = ctk.CTkButton(
            self.right_frame, 
            text="🧭 Calibrar Telescópio", 
            command=self.calibrate_telescope,
            state="disabled",  # Inicialmente desabilitado
            fg_color=COLOR_HIGHLIGHT,      # Azul escuro (combina com as setinhas)
            hover_color="#302C63",   # Azul mais claro no hover
            text_color="white",      # Texto branco
            width=120,               # Largura reduzida
            height=40,               # Altura reduzida
            corner_radius=20,        # Bordas arredondadas
            font=("Arial", 12, "bold")  # Fonte menor
        )
        self.btn_calibrate.grid(row=0, column=0, padx=10, pady=30, sticky="ew")

        # Frame para os botões de movimento (setinhas maiores)
        self.arrow_frame = ctk.CTkFrame(self.right_frame, fg_color=COLOR_BACKGROUND)
        self.arrow_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")  # Espaçamento ajustado

        # Configurar um grid 3x3 para as setinhas
        for col in range(3):
            self.arrow_frame.grid_columnconfigure(col, weight=1)
        for row in range(3):
            self.arrow_frame.grid_rowconfigure(row, weight=1)

        # Botão de cima (⬆️)
        self.btn_up = ctk.CTkButton(
            self.arrow_frame,
            text="↑",
            command=lambda: self.send_command("MOVE_UP"),
            state="enable",
            fg_color=COLOR_HIGHLIGHT,      # Azul escuro
            hover_color="#302C63",   # Azul mais claro no hover
            text_color="white",
            width=80,
            height=80,
            corner_radius=40,        # Bordas totalmente arredondadas
            font=("Arial", 24, "bold")
        )
        self.btn_up.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")  # Espaçamento reduzido

        # Botão de esquerda (⬅️)
        self.btn_left = ctk.CTkButton(
            self.arrow_frame,
            text="←",
            command=lambda: self.send_command("MOVE_LEFT"),
            state="enable",
            fg_color=COLOR_HIGHLIGHT,
            hover_color="#302C63",
            text_color="white",
            width=80,
            height=80,
            corner_radius=40,
            font=("Arial", 24, "bold")
        )
        self.btn_left.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")  # Espaçamento reduzido

        # Botão de direita (➡️)
        self.btn_right = ctk.CTkButton(
            self.arrow_frame,
            text="→",
            command=lambda: self.send_command("MOVE_RIGHT"),
            state="enable",
            fg_color=COLOR_HIGHLIGHT,
            hover_color="#302C63",
            text_color="white",
            width=80,
            height=80,
            corner_radius=40,
            font=("Arial", 24, "bold")
        )
        self.btn_right.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")  # Espaçamento reduzido

        # Botão de baixo (⬇️)
        self.btn_down = ctk.CTkButton(
            self.arrow_frame,
            text="↓",
            command=lambda: self.send_command("MOVE_DOWN"),
            state="enable",
            fg_color=COLOR_HIGHLIGHT,
            hover_color="#302C63",
            text_color="white",
            width=80,
            height=80,
            corner_radius=40,
            font=("Arial", 24, "bold")
        )
        self.btn_down.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")  # Espaçamento reduzido

        # -----------------------------
        # Botão "Visualizar Mapa Celeste" no meio da tela, abaixo dos elementos
        # -----------------------------
        self.btn_plot = ctk.CTkButton(
            self.main_frame,
            text="Visualizar Mapa Celeste",
            command=self.plot_sky,
            fg_color=COLOR_HIGHLIGHT,
            text_color=COLOR_TEXT_MAIN,
            hover_color="#1E90FF",
            width=100,
            height=40,
            corner_radius=20,
            font=("Arial", 14, "bold")
        )
        self.btn_plot.grid(row=2, column=0, columnspan=2, padx=30, pady=0, sticky="nsew")  # Centralizado na nova linha
    
    
        
    def plot_sky(self):
        sky_window = ctk.CTkToplevel(self)  # Cria uma nova janela
        sky_window.title("Mapa Celeste")
        sky_window.geometry("600x600")

        # Cria a frame para o gráfico na nova janela
        sky_plot = SkyPlotFrame(sky_window)
        sky_plot.pack(fill="both", expand=True)

        # Certifica-se de que ao fechar a janela o gráfico será atualizado
        sky_window.protocol("WM_DELETE_WINDOW", sky_window.destroy)

    def calibrate_telescope(self):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"CALIBRATE\n")
                self.connection_status.configure(text="✅ Calibração iniciada...", text_color="blue")
                
                # Simula a conclusão da calibração (substitua pela lógica real)
                time.sleep(25)  # Simula o tempo de calibração
                self.calibrated = True  # Marca a calibração como concluída
                
                # Exibe a mensagem de calibração
                self.connection_status.configure(text="✅ Norte e Altitude Calibrados!", text_color="blue")
                print("[PYTHON] Comandos de calibração enviados: Norte e Altitude")
                
                # Remove a mensagem após 15 segundos
                self.after(15000, self.clear_calibration_message)
                
                # Habilita os botões dos astros após a calibração
                self.update_astro_buttons()
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")
                self.calibrated = False  # Marca a calibração como falha
    
    def send_command(self, command):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(f"{command}\n".encode())
                self.connection_status.configure(text=f"✅ Comando enviado: {command}", text_color="blue")
                print(f"[PYTHON] Comando enviado: {command}")
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")
        else:
            self.connection_status.configure(text="❌ Erro: Conexão serial fechada", text_color="red")

                
    def clear_calibration_message(self):
        """Remove a mensagem de calibração após 15 segundos."""
        if self.serial_connection and self.serial_connection.is_open:
            self.connection_status.configure(text=f"✅ Conectado em {self.serial_connection.port}", text_color="green")
        else:
            self.connection_status.configure(text="⭕ Desconectado", text_color="red")

    def toggle_tracking(self): # Corrigido para aguardar o movimento POS
        if self.current_astro is None:
            self.connection_status.configure(text="❌ Selecione um astro primeiro!", text_color="red")
            return
        
        self.tracking_active = not self.tracking_active
        
        if self.tracking_active:
            self.btn_track.configure(text="⏸ Pausar Rastreamento", fg_color="#AA0000", hover_color="#880000")
            self.tracking_status.configure(text=f"Status: Rastreando {self.current_astro}", text_color="green")
            self.track_astro()
        else: # Pausa o rastreamento
            self.btn_track.configure(text="🔄 Retomar Rastreamento", fg_color="#00AA00", hover_color="#008800")
            self.tracking_status.configure(text="Status: Rastreamento pausado", text_color="orange")


    def track_astro(self):
        if self.tracking_active and self.current_astro:
            self.update_tracking_data() # Chama a função correta
            self.after(5000, self.track_astro)  # Atualiza a cada 5 segundos

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
                state="normal" if self.calibrated else "disabled"
            )
            btn.pack(fill="x", pady=2)
            self.astro_buttons.append(btn)

    def stop_tracking(self):
        self.tracking_active = False
        self.moving_to_position = False # Limpa o flag de movimento POS
        self.current_astro = None
        self.selected_astro = None

        self.btn_track.configure(text="🔄 Iniciar Rastreamento", fg_color="green", state="disabled") # Restaura o texto do botão
        self.btn_stop.configure(state="disabled")

        # Envia comando STOP para o Arduino
        self.send_command("STOP")

        self.lbl_altitude.configure(text="Altitude: --")
        self.lbl_azimute.configure(text="Azimute: --")
        self.tracking_status.configure(text="Status: Não está rastreando", text_color="gray") # Restaura a mensagem de status

    def get_astro_data(self):
        loader = Loader('~/skyfield-data')
        planets = loader('de421.bsp')
        ts = loader.timescale()
    
        # Coordenadas fixas de Formosa-GO
        latitude_observador = -15.541232599693457
        longitude_observador = -47.33334646343277
    
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
            portas = ['COM6']
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
                    
                    self.btn_calibrate.configure(state="normal")
                    
                    if self.serial_thread is None:
                        self.serial_thread = threading.Thread(target=self.read_from_serial, daemon=True)
                        self.serial_thread.start()
                    return
                except Exception:
                    continue
            raise Exception("Nenhuma porta encontrada!")
        except Exception as e:
            self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")
            self.btn_track.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.btn_calibrate.configure(state="disabled")

    def read_from_serial(self):
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
        if self.serial_connection and self.serial_connection.is_open:
            try:
                fator = 10
                safe_vel_alt = max(min(vel_alt * fator, 5.0), -5.0)
                safe_vel_azi = max(min(vel_azi * fator, 5.0), -5.0)
                comando = f"SPEED,{safe_vel_alt:.6f},{safe_vel_azi:.6f}\n"
                self.serial_connection.write(comando.encode('utf-8'))
                print(f"[PYTHON] Comando SPEED enviado: {comando.strip()}")
            except Exception as e:
                self.connection_status.configure(text=f"❌ Erro: {str(e)}", text_color="red")

    def send_position_command(self, alt, azi):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                adjusted_azi = (azi + self.azimuth_offset) % 360  # Garante que o valor fique entre 0° e 360°
                
                if not (-90 <= alt <= 90):
                    print("Coordenadas inválidas!")
                    return
            
                # Inverte a ordem: primeiro envia o azimute (ajustado) e depois a altitude
                comando = f"POS,{adjusted_azi:.2f},{alt:.2f}\n"
                self.serial_connection.write(comando.encode('utf-8'))
                print(f"[PYTHON] Comando POS enviado: {comando.strip()}")
                time.sleep(10)
            except Exception as e:
                print(f"Erro crítico ao enviar POS: {str(e)}")

    def select_astro(self, astro):
        self.current_astro = astro['nome']
        self.selected_astro = astro['nome']
        
        print(f"\n[DEBUG] Movendo para {astro['nome']}:")
        print(f"Altitude: {astro['altitude']:.2f}°")
        print(f"Azimute: {astro['azimute']:.2f}°")
        
        self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
        self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")
        
        self.btn_track.configure(state="normal")
        self.btn_stop.configure(state="normal")
        
        self.send_position_command(astro['altitude'], astro['azimute'])
        self.after(3000, lambda: self.btn_track.configure(state="normal")) # Habilita após 1 segundo
        self.after(3000, lambda: self.btn_stop.configure(state="normal"))
        

    def update_data(self):
        if self.tracking_active and self.current_astro:
            try:
                self.astros = self.get_astro_data()
                astro = next((a for a in self.astros if a['nome'] == self.current_astro), None)
                if astro:
                    vel_azi = astro['vel_azi']
                    vel_alt = astro['vel_alt']

                    fator = 2
                    safe_vel_alt = max(min(vel_alt * fator, 5.0), -5.0)
                    safe_vel_azi = max(min(vel_azi * fator, 5.0), -5.0)

                    if abs(safe_vel_azi) > 0.0001 or abs(safe_vel_alt) > 0.0001:
                        self.send_velocity_command(safe_vel_alt, safe_vel_azi)

                    self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
                    self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")
            except Exception as e:
                print(f"Erro no rastreamento: {str(e)}")
                
    def update_tracking_data(self): # Função renomeada e corrigida
        if self.tracking_active and self.current_astro:
            try:
                self.astros = self.get_astro_data()
                astro = next((a for a in self.astros if a['nome'] == self.current_astro), None)
                if astro:
                    self.send_velocity_command(astro['vel_alt'], astro['vel_azi']) # Envia velocidades diretamente
                    self.lbl_altitude.configure(text=f"Altitude: {astro['altitude']:.2f}°")
                    self.lbl_azimute.configure(text=f"Azimute: {astro['azimute']:.2f}°")
            except Exception as e:
                print(f"Erro no rastreamento: {str(e)}")

if __name__ == "__main__":
    app = TelescopeControl()
    app.mainloop()