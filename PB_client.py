import pickle
import pylab
import random
import select
import socket
import sys
import threading
import time
import uuid
from queue import Queue

import matplotlib
import pygame
import pygame_gui
import pygame_menu
from matplotlib.backends import backend_agg
from matplotlib.ticker import FuncFormatter

pygame.init()

matplotlib.use("Agg")

width = 900
height = 600


def run_in_thread(function):
    """Decorador que executa uma função como thread"""

    def run(*args, **kwargs):
        thread = threading.Thread(target=function, daemon=True, args=args, kwargs=kwargs)
        thread.start()

        return thread

    return run


def divide_chunks(l, n):
    """Divide uma lista em partes com o tamanho n"""
    for i in range(0, len(l), n):  
        yield l[i:i + n] 


class SocketManager(object):
    """Gerencia a troca de mensagens com o servidor"""

    def __init__(self):
        """Cria o objeto socket e a fila de mensagens"""
        self._socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.queue_inputs = Queue()
        self.outputs = {}

        self.lock_outputs = threading.Lock()

        self._loop_thread = None
        self._loop_running = True

    def connect(self, host: str, port: int):
        """Cria a conexão com o servidor"""
        self._socket_object.connect((host, port))

        self._loop_thread = threading.Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    @run_in_thread
    def update_data(self, command, update_function):
        """Adiciona uma mensagem a fila e aguarda ate receber uma resposta"""
        request_uuid = str(uuid.uuid4())
        self.queue_inputs.put({"uuid": request_uuid, "data": command})

        while True:
            with self.lock_outputs:
                if request_uuid in self.outputs.keys():
                    data = self.outputs[request_uuid]
                    self.outputs.pop(request_uuid)

                    break

        update_function(data)

    def _loop(self):
        """Troca mensagens com o servidor"""
        while self._loop_running:
            available_sockets = select.select([self._socket_object], [self._socket_object], [])

            if available_sockets[0]:
                data_fragments = []

                complete_data = False

                while not complete_data:
                    received_data = self._socket_object.recv(1024)

                    try:
                        formated_data = pickle.loads(received_data)

                        with self.lock_outputs:
                            self.outputs[formated_data["uuid"]] = formated_data["data"]

                        complete_data = True
                    except:
                        data_fragments.append(received_data)

                        try:
                            formated_data = pickle.loads(b"".join(data_fragments))

                            with self.lock_outputs:
                                self.outputs[formated_data["uuid"]] = formated_data["data"]

                            complete_data = True
                        except:
                            pass

            elif available_sockets[1] and not self.queue_inputs.empty():
                self._socket_object.send(pickle.dumps(self.queue_inputs.get()))

    def close(self):
        """Encerra a conexão com o servidor"""
        self._loop_running = False
        self._loop_thread.join()
        self._socket_object.close()


class ScreenManager(object):
    """Gerencia e exibe as páginas"""
    def __init__(self):
        self.screen = pygame.display.set_mode((width, height))
        self._pages = {}
        self.current_page = None
        self.clock = pygame.time.Clock()

    def add_page(self, page):
        """Adiciona uma página"""
        self._pages[page.name] = page

    def show_current_page(self):
        """Exibe a página atual"""
        page = self._pages[self.current_page]

        page.render()


class Page(pygame_gui.UIManager):
    def __init__(
        self, 
        name: str, 
        socket_manager: SocketManager,
        screen_manager: ScreenManager,
    ):
        super().__init__((width, height))

        self.name = name
        self._socket_manager = socket_manager
        self._screen_manager = screen_manager

        self.data = None
        self.data_lock = threading.Lock()

        self._screen_manager.add_page(self)

    def get_new_data(self):
        """Gerencia quando os dados tem que ser atualizados"""
        self.get_data_from_socket()

    def get_data_from_socket(self):
        """Pede para enviar uma mensagem ao servidor"""
        self._socket_manager.update_data(self.name, self.set_data)

    def set_data(self, new_data):
        """Formata os dados recebidos do servidor"""
        self.data = new_data
        self.update_screen()

    def update_screen(self):
        """Atualiza os dados na tela"""

    def render(self):
        """Renderiza um frame"""
        self.get_new_data()
        time_delta = self._screen_manager.clock.tick(30) / 1000.0
        self.update(time_delta)
        self.draw_ui(self._screen_manager.screen)


main_manager = pygame_gui.UIManager((900, 600))

btn_system = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 550), (150, 50)),
    text="SISTEMA",
    manager=main_manager,
)
btn_cpu = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((150, 550), (150, 50)),
    text="CPU",
    manager=main_manager,
)
btn_memory = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((300, 550), (150, 50)),
    text="MEMÓRIA",
    manager=main_manager,
)
btn_disk = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((450, 550), (150, 50)),
    text="DISCO",
    manager=main_manager,
)
btn_network = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((600, 550), (150, 50)),
    text="REDE",
    manager=main_manager,
)
btn_processes = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((750, 550), (150, 50)),
    text="PROCESSOS",
    manager=main_manager,
)

screen_manager = ScreenManager()
socket_manager = SocketManager()


class SystemPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.node_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 75), (600, 50)),
            text="",
            manager=self
        )
        self.system_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 125), (600, 50)),
            text="",
            manager=self
        )
        self.platform_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 175), (600, 50)),
            text="",
            manager=self
        )
        self.realese_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 225), (600, 50)),
            text="",
            manager=self
        )
        self.version_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 275), (600, 50)),
            text="",
            manager=self
        )
        self.python_version_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 325), (600, 50)),
            text="",
            manager=self
        )
        self.python_implementation_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 375), (600, 50)),
            text="",
            manager=self
        )
        self.python_compiler_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 425), (600, 50)),
            text="",
            manager=self
        )

    def get_data(self):
        if self.data is not None:
            self.get_data_from_socket()

    def update_screen(self):
        self.node_label.set_text(f"Nome do sistema: {self.data['name']}")
        self.system_label.set_text(f"Sistema operacional: {self.data['system']}")
        self.platform_label.set_text(f"Plataforma: {self.data['plataform']}")
        self.realese_label.set_text(f"Lançamento: {self.data['realese']}")
        self.version_label.set_text(f"Versão: {self.data['version']}")
        self.python_version_label.set_text(f"Versão do Python: {self.data['python_version']}")
        self.python_implementation_label.set_text(f"Implementação do Python: {self.data['python_implementation']}")
        self.python_compiler_label.set_text(f"Compilador do Python: {self.data['python_compiler']}")


class CpuPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data = {
            "usage": [], 
            "cores_usage": {}
        }

        self._initialized = False

        self.usage_graph_fig = pylab.figure(figsize=[7, 4], dpi=75)
        self.usage_graph = self.usage_graph_fig.gca()

        self.usage_graph.set_ylim(0, 100)
        self.usage_graph.set_xlim(1, 10)

        self.usage_graph.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y}%"))

        self.canvas = backend_agg.FigureCanvasAgg(self.usage_graph_fig)
        self.usage_graph_renderer = self.canvas.get_renderer()
        self.usage_graph_surf = None

        self.colors = []

        self.name_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 10), (600, 50)),
            text="",
            manager=self,
        )
        self.architecture_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 130), (250, 50)),
            text="",
            manager=self,
        )
        self.bits_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 180), (250, 50)),
            text="",
            manager=self,
        )
        self.min_frequency_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 230), (250, 50)),
            text="",
            manager=self,
        )
        self.max_frequency_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 280), (250, 50)),
            text="",
            manager=self,
        )
        self.current_frequency_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 330), (250, 50)),
            text="",
            manager=self,
        )
        self.physical_cores_number_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 380), (250, 50)),
            text="",
            manager=self,
        )
        self.cores_number_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 430), (250, 50)),
            text="",
            manager=self,
        )

    def init(self):
        if not self._initialized:
            self.get_new_data_loop()

        self._initialized = True

    @run_in_thread
    def get_new_data_loop(self):
        while True:
            self.get_new_data()
            time.sleep(4)

    def set_data(self, new_data):
        with self.data_lock:
            self.data["usage"].append(new_data["usage"])

            if len(self.data["usage"]) > 10:
                self.data["usage"] = self.data["usage"][1:]

            for core in range(new_data["cores_number"]):
                if core not in self.data["cores_usage"].keys():
                    self.data["cores_usage"][core] = []

                self.data["cores_usage"][core].append(new_data["cores_usage"][core])

                if len(self.data["cores_usage"][core]) > 10:
                    self.data["cores_usage"][core] = self.data["cores_usage"][core][1:]

            new_data.pop("usage")
            new_data.pop("cores_usage")

            self.data = {**self.data, **new_data}

            self.name_label.set_text(f"Modelo: {self.data['name']}")
            self.architecture_label.set_text(f"Arquitetura: {self.data['architecture']}")
            self.bits_label.set_text(f"Bits: {self.data['bits']}")
            self.min_frequency_label.set_text(f"Frequência mínima: {self.data['min_frequency']}hz")
            self.max_frequency_label.set_text(f"Frequência máxima: {self.data['max_frequency']}hz")
            self.current_frequency_label.set_text(f"Frequência atual: {self.data['current_frequency']}hz")
            self.physical_cores_number_label.set_text(f"Núcleos (físicos): {self.data['physical_cores_number']}")
            self.cores_number_label.set_text(f"Núcleos: {self.data['cores_number']}")

            if not self.colors:
                self.colors = ["#"+"".join([random.choice("0123456789ABCDEF") for j in range(6)]) for i in range(self.data["cores_number"] + 1)]

        self.update_screen()

    def update_screen(self):
        with self.data_lock:
            for line in self.usage_graph.get_lines():
                line.remove()

            self.usage_graph.plot(
                range(1, len(self.data["usage"]) + 1),
                self.data["usage"],
                self.colors[0], 
                label=f"Geral ({self.data['usage'][-1]})%")

        count = 1
        for core in self.data["cores_usage"].values():
            self.usage_graph.plot(
                range(1, len(core) + 1), 
                core, self.colors[count], 
                label=f"Núcleo {count} ({core[-1]}%)"
            )
            count += 1

        self.canvas.draw()
        self.usage_graph_raw_data = self.usage_graph_renderer.tostring_rgb()
        self.usage_graph_size = self.canvas.get_width_height()
        self.usage_graph_surf = pygame.image.fromstring(self.usage_graph_raw_data, self.usage_graph_size, "RGB")

        self.usage_graph.legend()

    def render(self):
        if self.usage_graph_surf is not None:
            time_delta = self._screen_manager.clock.tick(30) / 1000.0
            self.update(time_delta)

            self._screen_manager.screen.blit(self.usage_graph_surf, (300, 150))

            self.draw_ui(self._screen_manager.screen)


class RamPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data = {"percent_usage": []}

        self._initialized = False

        self.usage_graph_fig = pylab.figure(figsize=[7, 4], dpi=75)
        self.usage_graph = self.usage_graph_fig.gca()

        self.usage_graph.set_ylim(0, 100)
        self.usage_graph.set_xlim(1, 10)

        self.usage_graph.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y}%"))

        self.canvas = backend_agg.FigureCanvasAgg(self.usage_graph_fig)
        self.usage_graph_renderer = self.canvas.get_renderer()

        self.usage_graph_surf = None

        self.color = "#"+"".join([random.choice("0123456789ABCDEF") for j in range(6)])

        self.total_gb_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 200), (300, 50)),
            text="",
            manager=self
        )
        self.used_gb_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 250), (300, 50)),
            text="",
            manager=self
        )
        self.available_gb_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 300), (300, 50)),
            text="",
            manager=self
        )

    def init(self):
        if not self._initialized:
            self.get_new_data_loop()

        self._initialized = True

    @run_in_thread
    def get_new_data_loop(self):
        while True:
            self.get_new_data()
            time.sleep(4)

    def set_data(self, new_data):
        with self.data_lock:
            self.data["percent_usage"].append(new_data["percent_usage"])

            if len(self.data["percent_usage"]) > 10:
                self.data["percent_usage"] = self.data["percent_usage"][1:]

            self.data = {**new_data, **self.data}

        self.update_screen()

    def update_screen(self):
        with self.data_lock:
            for line in self.usage_graph.get_lines():
                line.remove()

            self.usage_graph.plot(
                range(1, len(self.data["percent_usage"]) + 1),  
                self.data["percent_usage"], 
                self.color, 
                label=f"Uso ({self.data['percent_usage'][-1]})%"
            )

            self.total_gb_label.set_text(f"Total: {self.data['total_gb']}gb")
            self.used_gb_label.set_text(f"Usado: {self.data['used_gb']}gb")
            self.available_gb_label.set_text(f"Disponível: {self.data['available_gb']}gb")

        self.canvas.draw()
        usage_graph_raw_data = self.usage_graph_renderer.tostring_rgb()
        usage_graph_size = self.canvas.get_width_height()
        self.usage_graph_surf = pygame.image.fromstring(usage_graph_raw_data, usage_graph_size, "RGB")

        self.usage_graph.legend()

    def render(self):
        if self.usage_graph_surf is not None:
            time_delta = self._screen_manager.clock.tick(30) / 1000.0
            self.update(time_delta)

            self._screen_manager.screen.blit(self.usage_graph_surf, (300, 130))

            self.draw_ui(self._screen_manager.screen)


class DiskPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.total_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((300, 225), (300, 50)),
            text="",
            manager=self
        )
        self.used_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((300, 275), (300, 50)),
            text="",
            manager=self
        )
        self.available_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((300, 325), (300, 50)),
            text="",
            manager=self
        )

    def get_data(self):
        if self.data is not None:
            self.get_data_from_socket()

    def update_screen(self):
        with self.data_lock:
            self.total_label.set_text(f"Total: {self.data['gize_gb']}gb")
            self.used_label.set_text(
                f"Usado: {self.data['used_gb']}gb ({self.data['used_percent']}%)"
            )
            self.available_label.set_text(
                f"Disponível: {self.data['available_gb']}gb ({self.data['available_percent']}%)"
            )


class NetworkPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.preload_fonts([{"name": "fira_code", "html_size": 14, "style": "bold"}])

        self.interfaces_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((200, 15), (100, 50)),
            text="Interfaces",
            manager=self
        )
        self.host_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((650, 15), (100, 50)),
            text="Hosts",
            manager=self
        )
        self.interfaces_text = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((0, 80), (450, 470)),
            html_text="", 
            manager=self,
        )
        self.hosts_text = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((450, 80), (450, 470)),
            html_text="", 
            manager=self
        )

        self.data_requested = False

    def get_new_data(self):
        if not self.data_requested:
            self.get_data_from_socket()

        self.data_requested = True

    def update_screen(self):
        interfaces_text_content = "<b>Interface - Endereço - Netmask</b>"

        for interface in self.data["interfaces"]:
            interfaces_text_content += f"<br>{interface['interface']} - {interface['address']} - {interface['netmask']}"

        hosts_text_content = "<b>Host - Nome - Status</b><br>"

        for host in self.data["hosts"]:
            hosts_text_content += f"<br> {host['host']} - {host['name']} - {host['state']}<br> Protocolos:"

            for protocol in host['protocols']:
                hosts_text_content += f"<br>  - {protocol['protocol']}<br>   Portas:<br>"

                for port in protocol['posts']:
                    hosts_text_content += f"    - {port['port']}: {port['state']}"


        self.interfaces_text.html_text = interfaces_text_content
        self.hosts_text.html_text=hosts_text_content

        self.interfaces_text.rebuild()
        self.hosts_text.rebuild()


class ProcessesPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.preload_fonts([{"name": "fira_code", "html_size": 14, "style": "bold"}])

        self.processes_text = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((0, 0), (900, 470)),
            html_text="", 
            manager=self
        )

        self.previous_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((175, 480), (100, 50)), 
            text="Anterior",
            manager=self,
        )

        self.next_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((625, 480), (100, 50)),
            text="Proximo",
            manager=self,
        )

        self.pages = []
        self.page = 1

    def update_screen(self):
        self.pages = list(divide_chunks(self.data, 22))

    def render(self):
        if self.pages:
            if self.page == 1:
                self.previous_button.disable()
            else:
                self.previous_button.enable()
            if self.page == len(self.pages) - 1:
                self.next_button.disable()
            else:
                self.next_button.enable()

            text = "<b>Nome - Memória usada - Percentagem da memória usada - Threads usados - Tempo em execução - Data de criação</b>"

            for process in self.pages[self.page]:
                text += f"<br>{process['name']} - {process['used_memory']} - {process['memory_use_percent']} - {process['used_threads']} - {process['created_time']} - {process['created_date']}"

            self.processes_text.html_text = text

            self.processes_text.rebuild()

        super().render()


system_page = SystemPage(
    name="system", 
    screen_manager=screen_manager, 
    socket_manager=socket_manager, 
)
cpu_page = CpuPage(
    name="cpu", 
    screen_manager=screen_manager, 
    socket_manager=socket_manager, 
)
ram_page = RamPage(
    name="ram", 
    screen_manager=screen_manager, 
    socket_manager=socket_manager, 
)
disk_page = DiskPage(
    name="disk",
    screen_manager=screen_manager,
    socket_manager=socket_manager,
)
network_page = NetworkPage(
    name="network",
    screen_manager=screen_manager,
    socket_manager=socket_manager,
)
processes_page = ProcessesPage(
    name="processes",
    screen_manager=screen_manager,
    socket_manager=socket_manager,
)

host = socket.gethostname()
port = ""


def set_server_host(value):
    global host

    host = value


def set_server_port(value):
    global port

    if value != "":
        port = int(value)
    else:
        port = 0


def main():
    """Loop principal da interface"""
    socket_manager.connect(host, port)

    clock = screen_manager.clock

    screen_manager.current_page = "system"

    running = True

    while running:
        time_delta = clock.tick(30) / 1000.0

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == btn_system:
                        screen_manager.current_page = "system"
                    if event.ui_element == btn_cpu:
                        cpu_page.init()
                        screen_manager.current_page = "cpu"
                    if event.ui_element == btn_memory:
                        ram_page.init()
                        screen_manager.current_page = "ram"
                    if event.ui_element == btn_disk:
                        screen_manager.current_page = "disk"
                    if event.ui_element == btn_network:
                        screen_manager.current_page = "network"
                    if event.ui_element == btn_processes:
                        screen_manager.current_page = "processes"
                    if event.ui_element == processes_page.next_button:
                        processes_page.page += 1
                    if event.ui_element == processes_page.previous_button:
                        processes_page.page -= 1

            main_manager.process_events(event)
            processes_page.process_events(event)

        main_manager.update(time_delta)

        screen_manager.screen.fill((255, 255, 255))

        screen_manager.show_current_page()

        main_manager.draw_ui(screen_manager.screen)

        pygame.display.update()

    pygame.display.quit()
    socket_manager.close()


menu = pygame_menu.Menu(400, 500, "Bem-vindo", theme=pygame_menu.themes.THEME_SOLARIZED)

menu.add_text_input("Servidor: ", default=socket.gethostname(), onchange=set_server_host)
menu.add_text_input("Porta: ", onchange=set_server_port)
menu.add_button("Conectar", main)
menu.add_button("Sair", pygame_menu.events.EXIT)

if __name__ == "__main__":
    try:
        menu.mainloop(screen_manager.screen)
    except pygame.error:
        sys.exit()
