import os
import json
import random
import math
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Triangle, PushMatrix, PopMatrix, Rotate
from kivy.core.window import Window
from kivy.core.audio import SoundLoader

Window.clearcolor = (0.02, 0.02, 0.08, 1)

class Pato:
    def __init__(self, largura_tela, altura_tela, modo_dificuldade="Médio", cenario="Cidade"):
        self.dificuldade = modo_dificuldade
        self.cenario = cenario
        
        escala = 1.15
        self.largura = 65 * escala
        self.altura = 40 * escala
        self.tamanho_cabeca = 26 * escala

        self.direcao = random.choice([-1, 1])
        
        if self.direcao == 1:
            self.x = -self.largura * 2
        else:
            self.x = largura_tela + self.largura

        min_y = max(altura_tela * 0.45, 200)
        max_y = max(altura_tela * 0.88, 300)
        self.y = random.uniform(min_y, max_y)

        if cenario == "Cidade":
            if modo_dificuldade == "Fácil":
                base_vel = random.uniform(7.0, 9.5)
            elif modo_dificuldade == "Médio":
                base_vel = random.uniform(11.0, 14.0)
            else:
                base_vel = random.uniform(14.0, 18.5)
        else:
            if modo_dificuldade == "Fácil":
                base_vel = random.uniform(2.5, 4.0)
            elif modo_dificuldade == "Médio":
                base_vel = random.uniform(4.0, 6.5)
            else:
                base_vel = random.uniform(6.5, 9.0)

        self.velocidade_x = base_vel * self.direcao
        self.velocidade_y = 0.0
        self.vivo = True
        self.velocidade_asa = random.uniform(20, 28)
        
        self.tempo_mudanca_direcao = random.uniform(0.15, 0.4)
        self.contador_tempo = 0

    def atualizar(self):
        if self.vivo:
            self.x += self.velocidade_x
            self.y += self.velocidade_y
            
            if self.dificuldade in ["Médio", "Difícil"]:
                self.contador_tempo += 1/60.0
                if self.contador_tempo >= self.tempo_mudanca_direcao:
                    self.contador_tempo = 0
                    self.tempo_mudanca_direcao = random.uniform(0.15, 0.4)
                    
                    if self.cenario == "Cidade":
                        max_vy = 4.5 if self.dificuldade == "Médio" else 6.5
                        self.velocidade_y = random.uniform(-max_vy, max_vy)
                        
                        if self.dificuldade == "Fácil" and random.random() < 0.20:
                            self.velocidade_x = random.uniform(7.0, 9.5) * self.direcao
                        elif self.dificuldade == "Médio" and random.random() < 0.25:
                            self.velocidade_x = random.uniform(11.0, 14.0) * self.direcao
                        elif self.dificuldade == "Difícil" and random.random() < 0.35:
                            self.velocidade_x = random.uniform(14.0, 18.5) * self.direcao
                    else:
                        max_vy = 2.0 if self.dificuldade == "Médio" else 3.0
                        self.velocidade_y = random.uniform(-max_vy, max_vy)
                        
                        if self.dificuldade == "Médio" and random.random() < 0.15:
                            self.velocidade_x = random.uniform(4.0, 6.5) * self.direcao
                        elif self.dificuldade == "Difícil" and random.random() < 0.25:
                            self.velocidade_x = random.uniform(6.5, 9.0) * self.direcao
        else:
            self.y -= 14
            self.x += self.velocidade_x * 0.1

    def tocado(self, touch_x, touch_y):
        if self.vivo:
            area_toque = self.largura * 1.3
            return (self.x - area_toque * 0.1 <= touch_x <= self.x + area_toque) and \
                   (self.y - self.altura * 0.5 <= touch_y <= self.y + self.altura + self.tamanho_cabeca)
        return False


class JogoCidadeNoturnaPatos(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.patos = []
        self.efeitos_sangue = []
        
        self.no_menu_inicial = True
        self.iniciado = False
        self.game_over = False
        self.pausado = False
        self.em_contagem = False
        self.contagem = 3

        self.patos_mortos = 0
        self.patos_escapados = 0
        self.limite_escapes = 3
        
        # --- SISTEMA DE MISSÕES E PROGRESSÃO ---
        self.missao_atual_idx = 0
        self.missoes = [
            {"descricao": "Missão 1: Abata 5 patos", "alvo": 5, "concluida": False},
            {"descricao": "Missão 2: Abata 15 patos", "alvo": 15, "concluida": False},
            {"descricao": "Missão 3: Abata 30 patos", "alvo": 30, "concluida": False},
            {"descricao": "Missão 4: Mestre dos Patos (50 abates)", "alvo": 50, "concluida": False}
        ]

        # --- CARREGAR RECORDE SALVO ---
        self.arquivo_recorde = "recorde.json"
        self.maior_recorde = self.carregar_recorde()

        self.dificuldade_atual = "Médio"
        self.cenario_atual = "Cidade"
        self.limite_patos = 7
        self.event_spawn = None

        self.angulo_mira = 45.0
        self.tempo_tiro = 0.0

        self.estrelas = []
        self.predios_frente = []

        # --- CARREGAMENTO DE SONS ---
        self.som_menu = SoundLoader.load('menu_sound.wav')
        self.som_tiro = SoundLoader.load('shot_sound.wav')

        if self.som_menu:
            self.som_menu.loop = True
            self.som_menu.play()

        self.desenho_widget = Widget()
        self.add_widget(self.desenho_widget)

        # --- MENU INICIAL ---
        self.box_menu_inicial = BoxLayout(
            orientation='vertical',
            size_hint=(0.85, 0.65),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=12,
            padding=10
        )

        self.lbl_titulo = Label(
            text="Strike Pato",
            font_size='48sp',
            bold=True,
            color=(1, 0.85, 0.1, 1)
        )

        self.lbl_recorde_menu = Label(
            text=f"🏆 Maior Recorde: {self.maior_recorde}",
            font_size='20sp',
            bold=True,
            color=(0.2, 0.9, 1, 1)
        )

        self.btn_jogar = Button(
            text="JOGAR",
            font_size='22sp',
            bold=True,
            size_hint=(1, 0.25),
            background_color=(0.2, 0.8, 0.3, 1)
        )
        self.btn_jogar.bind(on_release=self.iniciar_partida_do_menu)

        self.btn_missoes = Button(
            text="📜 Missões",
            font_size='18sp',
            size_hint=(1, 0.2),
            background_color=(0.8, 0.5, 0.1, 1)
        )
        self.btn_missoes.bind(on_release=self.abrir_menu_missoes)

        self.btn_config = Button(
            text="Configurações",
            font_size='18sp',
            size_hint=(1, 0.2),
            background_color=(0.2, 0.4, 0.7, 1)
        )
        self.btn_config.bind(on_release=self.abrir_menu)

        self.box_menu_inicial.add_widget(self.lbl_titulo)
        self.box_menu_inicial.add_widget(self.lbl_recorde_menu)
        self.box_menu_inicial.add_widget(self.btn_jogar)
        self.box_menu_inicial.add_widget(self.btn_missoes)
        self.box_menu_inicial.add_widget(self.btn_config)
        self.add_widget(self.box_menu_inicial)

        # --- ASSINATURA / NOME DO JOGADOR NO CANTO INFERIOR DIREITO ---
        self.lbl_assinatura = Label(
            text="MC LP Medeiros",
            font_size='14sp',
            color=(0.7, 0.7, 0.7, 0.8),
            size_hint=(None, None),
            size=(200, 30),
            pos_hint={'right': 0.98, 'y': 0.02},
            halign='right'
        )
        self.add_widget(self.lbl_assinatura)

        # --- FRASE NO CANTO INFERIOR ESQUERDO ---
        self.lbl_bonde = Label(
            text="bonde da VP",
            font_size='14sp',
            color=(0.7, 0.7, 0.7, 0.8),
            size_hint=(None, None),
            size=(200, 30),
            pos_hint={'x': 0.02, 'y': 0.02},
            halign='left'
        )
        self.add_widget(self.lbl_bonde)

        # --- MARCA D'ÁGUA NO CENTRO DA TELA ---
        self.lbl_marca_dagua_centro = Label(
            text="bonde da VP",
            font_size='42sp',
            bold=True,
            color=(1, 1, 1, 0.12),
            size_hint=(None, None),
            size=(400, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.58},
            halign='center',
            valign='middle'
        )
        self.lbl_marca_dagua_centro.bind(size=self.lbl_marca_dagua_centro.setter('text_size'))
        self.add_widget(self.lbl_marca_dagua_centro)

        # --- HUD DO JOGO ---
        self.btn_menu = Button(
            text="Menu",
            size_hint=(0.18, 0.07),
            pos_hint={'x': 0.02, 'top': 0.98},
            background_color=(0.15, 0.2, 0.3, 0.95),
            font_size='16sp'
        )
        self.btn_menu.bind(on_release=self.abrir_menu)

        self.lbl_contador = Label(
            text="",
            size_hint=(0.6, 0.09),
            pos_hint={'x': 0.38, 'top': 0.99},
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            halign='right',
            valign='top'
        )
        self.lbl_contador.bind(size=self.lbl_contador.setter('text_size'))

        self.lbl_contagem = Label(
            text="",
            font_size='72sp',
            bold=True,
            color=(1, 0.9, 0.2, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.55}
        )
        self.add_widget(self.lbl_contagem)

        # --- TELA GAME OVER ---
        self.box_game_over = BoxLayout(
            orientation='vertical',
            size_hint=(0.6, 0.35),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=20,
            spacing=10
        )

        self.lbl_game_over = Label(
            text="GAME OVER!\n3 patos escaparam!",
            font_size='20sp',
            bold=True,
            color=(1, 0.3, 0.3, 1),
            halign='center'
        )
        self.btn_restart = Button(
            text="Reiniciar Jogo",
            size_hint=(1, 0.35),
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='18sp',
            bold=True
        )
        self.btn_restart.bind(on_release=self.reiniciar_jogo)

        self.btn_voltar_menu = Button(
            text="Menu Inicial",
            size_hint=(1, 0.3),
            background_color=(0.3, 0.4, 0.6, 1),
            font_size='16sp'
        )
        self.btn_voltar_menu.bind(on_release=self.voltar_ao_menu_inicial)

        self.box_game_over.add_widget(self.lbl_game_over)
        self.box_game_over.add_widget(self.btn_restart)
        self.box_game_over.add_widget(self.btn_voltar_menu)

        self.bind(size=self.redimensionar_cenario)

    def carregar_recorde(self):
        try:
            if os.path.exists(self.arquivo_recorde):
                with open(self.arquivo_recorde, 'r') as f:
                    dados = json.load(f)
                    return dados.get("recorde", 0)
        except Exception:
            pass
        return 0

    def salvar_recorde(self, valor):
        try:
            with open(self.arquivo_recorde, 'w') as f:
                json.dump({"recorde": valor}, f)
        except Exception:
            pass

    def redimensionar_cenario(self, *args):
        if self.width <= 100 or self.height <= 100:
            return
        Clock.schedule_once(self._inicializar_elementos_cenario, 0.05)

    def _inicializar_elementos_cenario(self, dt):
        if self.width <= 100 or self.height <= 100:
            return

        self.estrelas = [
            (random.uniform(0, self.width), random.uniform(self.height * 0.4, self.height), random.uniform(1.5, 2.5))
            for _ in range(30)
        ]

        self.predios_frente = []
        x_atual = 0.0
        while x_atual < self.width:
            largura = random.uniform(80, 130)
            altura = random.uniform(self.height * 0.25, self.height * 0.45)
            cor_tom = random.uniform(0.08, 0.15)

            janelas = []
            colunas = int(largura // 18)
            linhas = int(altura // 22)
            for col in range(max(1, colunas)):
                for lin in range(max(1, linhas)):
                    if random.random() > 0.45:
                        janelas.append((x_atual + 8 + (col * 16), (self.height * 0.18) + 10 + (lin * 19)))

            self.predios_frente.append({
                'x': x_atual,
                'l': largura,
                'a': altura,
                'cor': (cor_tom, cor_tom + 0.03, cor_tom + 0.08),
                'janelas': janelas
            })
            x_atual += max(20.0, largura - 2)

        if not self.iniciado:
            self.iniciado = True
            Clock.schedule_interval(self.atualizar_jogo, 1 / 60)

    def iniciar_partida_do_menu(self, instance=None):
        if self.som_menu:
            self.som_menu.stop()

        if self.box_menu_inicial in self.children:
            self.remove_widget(self.box_menu_inicial)
        if self.lbl_assinatura in self.children:
            self.remove_widget(self.lbl_assinatura)
        if self.lbl_bonde in self.children:
            self.remove_widget(self.lbl_bonde)
        
        self.no_menu_inicial = False
        self.patos.clear()
        self.efeitos_sangue.clear()
        self.patos_mortos = 0
        self.patos_escapados = 0
        self.game_over = False
        
        self.add_widget(self.btn_menu)
        self.add_widget(self.lbl_contador)
        self.atualizar_hud()
        self.agendar_spawn()
        self.iniciar_contagem_regressiva()

    def voltar_ao_menu_inicial(self, instance=None, popup=None):
        if popup:
            popup.dismiss()

        if self.event_spawn:
            self.event_spawn.cancel()

        self.patos.clear()
        self.efeitos_sangue.clear()
        self.no_menu_inicial = True
        self.pausado = False
        self.game_over = False
        self.em_contagem = False
        self.lbl_contagem.text = ""

        if self.btn_menu in self.children:
            self.remove_widget(self.btn_menu)
        if self.lbl_contador in self.children:
            self.remove_widget(self.lbl_contador)
        if self.box_game_over in self.children:
            self.remove_widget(self.box_game_over)

        if self.som_menu:
            self.som_menu.play()

        self.lbl_recorde_menu.text = f"🏆 Maior Recorde: {self.maior_recorde}"
        if self.box_menu_inicial not in self.children:
            self.add_widget(self.box_menu_inicial)
        if self.lbl_assinatura not in self.children:
            self.add_widget(self.lbl_assinatura)
        if self.lbl_bonde not in self.children:
            self.add_widget(self.lbl_bonde)

    def calcular_intervalo_spawn(self):
        if self.dificuldade_atual == "Fácil":
            return 1.8
        elif self.dificuldade_atual == "Médio":
            return 0.8
        else:
            return 0.40

    def agendar_spawn(self):
        if self.event_spawn:
            self.event_spawn.cancel()

        intervalo = self.calcular_intervalo_spawn()
        self.event_spawn = Clock.schedule_interval(self.gerar_pato, intervalo)

    def gerar_pato(self, dt):
        if not self.no_menu_inicial and not self.game_over and not self.pausado and not self.em_contagem and len(self.patos) < self.limite_patos and self.width > 100:
            self.patos.append(Pato(self.width, self.height, modo_dificuldade=self.dificuldade_atual, cenario=self.cenario_atual))

    def iniciar_contagem_regressiva(self):
        self.em_contagem = True
        self.contagem = 3
        self.lbl_contagem.text = str(self.contagem)
        Clock.schedule_interval(self.atualizar_contagem, 1.0)

    def atualizar_contagem(self, dt):
        self.contagem -= 1
        if self.contagem > 0:
            self.lbl_contagem.text = str(self.contagem)
        elif self.contagem == 0:
            self.lbl_contagem.text = "VAI!"
        else:
            self.lbl_contagem.text = ""
            self.em_contagem = False
            self.pausado = False
            return False

    def atualizar_jogo(self, dt):
        if not self.iniciado or self.game_over:
            return

        if self.no_menu_inicial or self.pausado or self.em_contagem:
            self.desenhar_cena()
            return

        if self.tempo_tiro > 0:
            self.tempo_tiro -= dt

        for sangue in self.efeitos_sangue[:]:
            sangue['tempo'] -= dt
            sangue['escorrer'] += 1.2
            if sangue['tempo'] <= 0:
                self.efeitos_sangue.remove(sangue)

        altura_chao = self.height * 0.18

        for pato in self.patos[:]:
            pato.atualizar()

            no_chao = pato.y <= (altura_chao - pato.altura)
            fora_da_tela = (pato.x < -200 and pato.velocidade_x < 0) or (pato.x > self.width + 200 and pato.velocidade_x > 0)

            if no_chao:
                self.patos.remove(pato)
            elif fora_da_tela:
                if pato.vivo:
                    self.patos_escapados += 1
                    self.atualizar_hud()
                    if self.patos_escapados >= self.limite_escapes:
                        self.disparar_game_over()

                self.patos.remove(pato)

        self.desenhar_cena()

    def verificar_missoes(self):
        if self.missao_atual_idx < len(self.missoes):
            m = self.missoes[self.missao_atual_idx]
            if not m["concluida"] and self.patos_mortos >= m["alvo"]:
                m["concluida"] = True
                self.missao_atual_idx += 1
                self.mostrar_popup_missao_concluida(m["descricao"])

    def mostrar_popup_missao_concluida(self, texto_missao):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(text="🎉 MISSÃO CONCLUÍDA! 🎉", font_size='20sp', bold=True, color=(1, 0.8, 0.2, 1)))
        content.add_widget(Label(text=texto_missao, font_size='16sp', halign='center'))
        
        btn_ok = Button(text="Continuar", size_hint=(1, 0.4), background_color=(0.2, 0.7, 0.3, 1))
        p = Popup(title="Parabéns!", content=content, size_hint=(0.7, 0.4), auto_dismiss=False)
        btn_ok.bind(on_release=p.dismiss)
        content.add_widget(btn_ok)
        p.open()

    def abrir_menu_missoes(self, instance):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="📜 Lista de Missões", font_size='20sp', bold=True, color=(1, 0.8, 0.2, 1)))

        for m in self.missoes:
            status = "✅ Concluída" if m["concluida"] else "⏳ Em Aberto"
            cor = (0.2, 0.8, 0.3, 1) if m["concluida"] else (0.8, 0.6, 0.2, 1)
            layout.add_widget(Label(text=f"{m['descricao']} - {status}", font_size='14sp', color=cor))

        btn_fechar = Button(text="Voltar", size_hint=(1, 0.3), background_color=(0.3, 0.4, 0.6, 1))
        popup = Popup(title="Missões", content=layout, size_hint=(0.8, 0.6), auto_dismiss=True)
        btn_fechar.bind(on_release=popup.dismiss)
        layout.add_widget(btn_fechar)
        popup.open()

    def atualizar_hud(self):
        if self.patos_mortos > self.maior_recorde:
            self.maior_recorde = self.patos_mortos
            self.salvar_recorde(self.maior_recorde)
            
        self.verificar_missoes()
        
        m_txt = ""
        if self.missao_atual_idx < len(self.missoes):
            m = self.missoes[self.missao_atual_idx]
            m_txt = f"\n🎯 Missão: {self.patos_mortos}/{m['alvo']}"

        self.lbl_contador.text = f"Mortos: {self.patos_mortos} | Fugiram: {self.patos_escapados}/{self.limite_escapes}\n🏆 Recorde: {self.maior_recorde}{m_txt}"

    def disparar_game_over(self):
        self.game_over = True
        if self.event_spawn:
            self.event_spawn.cancel()
        self.add_widget(self.box_game_over)

    def reiniciar_jogo(self, instance=None):
        if self.box_game_over in self.children:
            self.remove_widget(self.box_game_over)

        self.patos.clear()
        self.efeitos_sangue.clear()
        self.patos_mortos = 0
        self.patos_escapados = 0
        self.game_over = False
        self.pausado = False
        self.em_contagem = False
        self.lbl_contagem.text = ""
        self.atualizar_hud()
        self.agendar_spawn()
        self.iniciar_contagem_regressiva()

    def on_touch_down(self, touch):
        if self.no_menu_inicial or self.game_over or self.pausado or self.em_contagem:
            return super().on_touch_down(touch)

        if self.btn_menu.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        for pato in reversed(self.patos):
            if pato.tocado(touch.x, touch.y):
                pato.vivo = False
                self.patos_mortos += 1
                self.atualizar_hud()

                self.efeitos_sangue.append({
                    'x': pato.x + pato.largura / 2,
                    'y': pato.y + pato.altura / 2,
                    'tempo': 0.7,
                    'escorrer': 0.0
                })

                if self.som_tiro:
                    self.som_tiro.play()

                origem_x = self.width * 0.50
                origem_y = (self.height * 0.22) + 85
                dx = touch.x - origem_x
                dy = touch.y - origem_y
                
                self.angulo_mira = math.degrees(math.atan2(dy, dx))
                self.tempo_tiro = 0.28
                return True

        return super().on_touch_down(touch)

    def aplicar_dificuldade(self, nivel):
        self.dificuldade_atual = nivel

        if nivel == "Fácil":
            self.limite_patos = 3
        elif nivel == "Médio":
            self.limite_patos = 7
        elif nivel == "Difícil":
            self.limite_patos = 10

        if not self.no_menu_inicial:
            self.agendar_spawn()

    def aplicar_cenario_com_contagem(self, cenario, popup):
        self.cenario_atual = cenario
        popup.dismiss()
        if not self.no_menu_inicial:
            self.iniciar_contagem_regressiva()

    def despausar_e_fechar(self, popup):
        if not self.no_menu_inicial:
            self.pausado = False
        popup.dismiss()

    def abrir_menu(self, instance):
        if not self.no_menu_inicial:
            self.pausado = True

        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        lbl_dif = Label(text=f"Dificuldade: {self.dificuldade_atual}", font_size='16sp', bold=True)
        layout.add_widget(lbl_dif)

        box_botoes_dif = BoxLayout(orientation='horizontal', spacing=8, size_hint=(1, 0.22))
        btn_facil = Button(text="Fácil", background_color=(0.2, 0.8, 0.2, 1) if self.dificuldade_atual == "Fácil" else (0.4, 0.4, 0.4, 1))
        btn_medio = Button(text="Médio ⚡", background_color=(0.9, 0.7, 0.1, 1) if self.dificuldade_atual == "Médio" else (0.4, 0.4, 0.4, 1))
        btn_dificil = Button(text="DIFÍCIL 🔥", background_color=(0.9, 0.2, 0.2, 1) if self.dificuldade_atual == "Difícil" else (0.4, 0.4, 0.4, 1))

        box_botoes_dif.add_widget(btn_facil)
        box_botoes_dif.add_widget(btn_medio)
        box_botoes_dif.add_widget(btn_dificil)
        layout.add_widget(box_botoes_dif)

        lbl_cen = Label(text=f"Cenário: {self.cenario_atual}", font_size='16sp', bold=True)
        layout.add_widget(lbl_cen)

        box_botoes_cen = BoxLayout(orientation='horizontal', spacing=8, size_hint=(1, 0.22))
        btn_cidade = Button(text="Cidade 🏙️", background_color=(0.2, 0.5, 0.8, 1) if self.cenario_atual == "Cidade" else (0.4, 0.4, 0.4, 1))
        btn_casa = Button(text="Casa 🏡", background_color=(0.8, 0.5, 0.2, 1) if self.cenario_atual == "Casa" else (0.4, 0.4, 0.4, 1))
        btn_montanha = Button(text="Montanhas ⛰️", background_color=(0.3, 0.7, 0.4, 1) if self.cenario_atual == "Montanhas" else (0.4, 0.4, 0.4, 1))

        box_botoes_cen.add_widget(btn_cidade)
        box_botoes_cen.add_widget(btn_casa)
        box_botoes_cen.add_widget(btn_montanha)
        layout.add_widget(box_botoes_cen)

        popup = Popup(
            title="Menu & Configurações",
            content=layout,
            size_hint=(0.88, 0.65),
            auto_dismiss=False
        )

        btn_facil.bind(on_release=lambda i: [self.aplicar_dificuldade("Fácil"), self.despausar_e_fechar(popup)])
        btn_medio.bind(on_release=lambda i: [self.aplicar_dificuldade("Médio"), self.despausar_e_fechar(popup)])
        btn_dificil.bind(on_release=lambda i: [self.aplicar_dificuldade("Difícil"), self.despausar_e_fechar(popup)])

        btn_cidade.bind(on_release=lambda i: self.aplicar_cenario_com_contagem("Cidade", popup))
        btn_casa.bind(on_release=lambda i: self.aplicar_cenario_com_contagem("Casa", popup))
        btn_montanha.bind(on_release=lambda i: self.aplicar_cenario_com_contagem("Montanhas", popup))

        if not self.no_menu_inicial:
            btn_sair_jogo = Button(
                text="🚪 Sair para o Menu Inicial",
                size_hint=(1, 0.22),
                background_color=(0.8, 0.2, 0.2, 1)
            )
            btn_sair_jogo.bind(on_release=lambda i: self.voltar_ao_menu_inicial(popup=popup))
            layout.add_widget(btn_sair_jogo)

        btn_fechar = Button(
            text="Voltar ao Jogo" if not self.no_menu_inicial else "Confirmar",
            size_hint=(1, 0.22),
            background_color=(0.2, 0.6, 0.3, 1)
        )
        btn_fechar.bind(on_release=lambda i: self.despausar_e_fechar(popup))
        layout.add_widget(btn_fechar)

        popup.open()

    def desenhar_cacador_3d(self, cx, cy):
        Color(0, 0, 0, 0.45)
        Ellipse(pos=(cx - 42, cy - 16), size=(84, 20))

        Color(0.08, 0.05, 0.02, 1)
        Rectangle(pos=(cx - 32, cy - 10), size=(28, 22))
        Rectangle(pos=(cx + 4, cy - 10), size=(28, 22))
        Color(0.25, 0.18, 0.1, 0.6)
        Rectangle(pos=(cx - 30, cy + 2), size=(24, 6))
        Rectangle(pos=(cx + 6, cy + 2), size=(24, 6))

        Color(0.15, 0.22, 0.12, 1)
        Rectangle(pos=(cx - 30, cy + 12), size=(24, 48))
        Rectangle(pos=(cx + 6, cy + 12), size=(24, 48))
        Color(0.05, 0.1, 0.05, 0.7)
        Rectangle(pos=(cx - 6, cy + 12), size=(12, 48))

        Color(0.12, 0.20, 0.11, 1)
        Rectangle(pos=(cx - 38, cy + 60), size=(76, 62))
        Color(0.22, 0.35, 0.20, 1)
        Rectangle(pos=(cx - 38, cy + 108), size=(76, 14))
        Color(0.95, 0.40, 0.0, 1)
        Rectangle(pos=(cx - 38, cy + 92), size=(76, 14))
        Color(1.0, 0.65, 0.2, 0.8)
        Rectangle(pos=(cx - 38, cy + 104), size=(76, 2))

        Color(0.85, 0.62, 0.46, 1)
        Ellipse(pos=(cx - 26, cy + 122), size=(52, 52))
        Color(0.22, 0.12, 0.05, 1)
        Rectangle(pos=(cx - 26, cy + 122), size=(52, 22))
        Color(0.12, 0.06, 0.02, 0.5)
        Ellipse(pos=(cx - 22, cy + 118), size=(44, 18))

        Color(0.1, 0.16, 0.08, 1)
        Ellipse(pos=(cx - 52, cy + 158), size=(104, 22))
        Color(0.14, 0.22, 0.12, 1)
        Rectangle(pos=(cx - 32, cy + 166), size=(64, 30))
        Color(0.25, 0.38, 0.2, 0.8)
        Ellipse(pos=(cx - 30, cy + 182), size=(60, 14))

        PushMatrix()
        ponto_rotacao = (cx, cy + 95)
        Rotate(angle=self.angulo_mira, origin=ponto_rotacao)

        Color(0, 0, 0, 0.3)
        Rectangle(pos=(cx - 28, cy + 82), size=(170, 12))

        Color(0.35, 0.18, 0.06, 1)
        Rectangle(pos=(cx - 28, cy + 88), size=(60, 18))
        Color(0.5, 0.28, 0.12, 0.6)
        Rectangle(pos=(cx - 28, cy + 102), size=(60, 4))

        Color(0.15, 0.15, 0.18, 1)
        Rectangle(pos=(cx + 32, cy + 92), size=(110, 10))
        Color(0.4, 0.4, 0.45, 0.9)
        Rectangle(pos=(cx + 32, cy + 99), size=(110, 3))

        Color(0.05, 0.05, 0.08, 1)
        Rectangle(pos=(cx + 15, cy + 105), size=(45, 10))
        Color(0.2, 0.7, 1.0, 0.7)
        Ellipse(pos=(cx + 56, cy + 106), size=(5, 8))

        if self.tempo_tiro > 0:
            Color(1, 0.95, 0.4, 0.3)
            Ellipse(pos=(cx + 110, cy + 45), size=(120, 100))
            Color(1, 0.9, 0.2, 0.98)
            Ellipse(pos=(cx + 138, cy + 72), size=(65, 50))
            Color(1, 0.4, 0.0, 0.95)
            Ellipse(pos=(cx + 145, cy + 78), size=(45, 38))
            Color(1, 1, 0.8, 1.0)
            Ellipse(pos=(cx + 152, cy + 85), size=(25, 22))

        PopMatrix()

    def desenhar_cena(self, *args):
        if self.width <= 10 or self.height <= 10 or not self.iniciado:
            return

        if self.no_menu_inicial:
            if self.lbl_marca_dagua_centro in self.children:
                self.remove_widget(self.lbl_marca_dagua_centro)
        else:
            if self.lbl_marca_dagua_centro not in self.children:
                self.add_widget(self.lbl_marca_dagua_centro)

        canvas = self.desenho_widget.canvas
        canvas.clear()

        tempo = Clock.get_time()
        altura_chao = self.height * 0.18

        with canvas:
            if self.cenario_atual == "Cidade":
                num_fatias_ceu = 6
                for i in range(num_fatias_ceu):
                    fator = i / num_fatias_ceu
                    r = 0.02 + (0.04 * fator)
                    g = 0.03 + (0.05 * fator)
                    b = 0.10 + (0.15 * fator)
                    Color(r, g, b, 1)
                    Rectangle(pos=(0, i * (self.height / num_fatias_ceu)), size=(self.width, (self.height / num_fatias_ceu) + 1))

                Color(1, 1, 0.88, 1)
                Ellipse(pos=(self.width * 0.78, self.height * 0.78), size=(55, 55))

                for ex, ey, tam in self.estrelas:
                    Color(1, 1, 1, 0.8)
                    Ellipse(pos=(ex, ey), size=(tam, tam))

                for p in self.predios_frente:
                    Color(*p['cor'])
                    Rectangle(pos=(p['x'], altura_chao), size=(p['l'], p['a']))
                    
                    for jx, jy in p['janelas']:
                        Color(1, 0.92, 0.6, 0.8)
                        Rectangle(pos=(jx, jy), size=(8, 12))

                Color(0.22, 0.22, 0.25, 1)
                Rectangle(pos=(0, altura_chao - 12), size=(self.width, 12))
                Color(0.10, 0.10, 0.12, 1)
                Rectangle(pos=(0, 0), size=(self.width, altura_chao - 12))

                Color(0.8, 0.8, 0.2, 0.6)
                for rx in range(0, int(self.width), 45):
                    Rectangle(pos=(rx, altura_chao - 7), size=(25, 3))

                cx = self.width * 0.50
                cy = altura_chao - 5
                self.desenhar_cacador_3d(cx, cy)

            elif self.cenario_atual == "Casa":
                for i in range(6):
                    fator = i / 6
                    Color(0.15 + 0.5*fator, 0.08 + 0.18*fator, 0.25 - 0.15*fator, 1)
                    Rectangle(pos=(0, i * (self.height/6)), size=(self.width, (self.height/6) + 1))

                Color(1, 0.7, 0.2, 0.8)
                Ellipse(pos=(self.width * 0.2, self.height * 0.45), size=(100, 100))

                Color(0.15, 0.4, 0.15, 1)
                Rectangle(pos=(0, 0), size=(self.width, altura_chao))

                casa_x = self.width * 0.15
                Color(0.7, 0.6, 0.5, 1)
                Rectangle(pos=(casa_x, altura_chao), size=(140, 100))
                Color(0.6, 0.15, 0.1, 1)
                Triangle(points=[casa_x - 15, altura_chao + 100, casa_x + 70, altura_chao + 160, casa_x + 155, altura_chao + 100])
                Color(0.3, 0.2, 0.1, 1)
                Rectangle(pos=(casa_x + 50, altura_chao), size=(35, 60))

                cx = self.width * 0.50
                cy = altura_chao - 5
                self.desenhar_cacador_3d(cx, cy)

            else:
                num_fatias = 8
                for i in range(num_fatias):
                    fator = i / num_fatias
                    r = 0.05 + (0.30 * fator)
                    g = 0.05 + (0.12 * fator)
                    b = 0.20 + (0.30 * fator)
                    Color(r, g, b, 1)
                    Rectangle(pos=(0, i * (self.height/num_fatias)), size=(self.width, (self.height/num_fatias) + 1))

                Color(1, 0.98, 0.9, 0.95)
                Ellipse(pos=(self.width * 0.78, self.height * 0.70), size=(70, 70))

                Color(0.12, 0.14, 0.28, 1)
                Ellipse(pos=(-self.width * 0.15, self.height * 0.18), size=(self.width * 0.65, self.height * 0.52))
                
                Color(0.08, 0.18, 0.16, 1)
                Ellipse(pos=(-self.width * 0.22, -self.height * 0.10), size=(self.width * 0.75, self.height * 0.48))

                Color(0.04, 0.12, 0.08, 1)
                Rectangle(pos=(0, 0), size=(self.width, self.height * 0.18))

                morro_largura = self.width * 0.88
                morro_altura = self.height * 0.38
                morro_x = (self.width - morro_largura) / 2
                morro_y = -self.height * 0.12

                Color(0.07, 0.26, 0.14, 1)
                Ellipse(pos=(morro_x, morro_y), size=(morro_largura, morro_altura))

                cx = self.width * 0.50
                cy = (morro_y + morro_altura * 0.92)
                self.desenhar_cacador_3d(cx, cy)

            # Desenho do Sangue Escorrendo em formato de Funil
            for sangue in self.efeitos_sangue:
                sx = sangue['x']
                sy = sangue['y']
                escorreu = sangue['escorrer']

                Color(0.75, 0.05, 0.05, 0.9)
                Ellipse(pos=(sx - 18, sy - 12), size=(36, 26))
                Color(0.4, 0.0, 0.0, 0.9)
                Ellipse(pos=(sx - 8, sy - 5), size=(16, 12))

                Color(0.68, 0.02, 0.02, 0.88)
                Triangle(points=[
                    sx - 6, sy - 10,
                    sx + 6, sy - 10,
                    sx, sy - 16 - (escorreu * 1.5)
                ])

                Color(0.8, 0.05, 0.05, 0.95)
                Ellipse(pos=(sx - 2.5, sy - 19 - (escorreu * 1.5)), size=(5, 7))

            if not self.no_menu_inicial:
                for pato in self.patos:
                    PushMatrix()

                    cor_corpo = (1, 0.85, 0.1, 1)
                    cor_bico = (1, 0.45, 0, 1)
                    olhando_direita = pato.direcao == 1

                    p_x = pato.x
                    p_y = pato.y

                    if not pato.vivo:
                        Rotate(angle=tempo * 120 * pato.direcao, origin=(p_x + pato.largura / 2, p_y + pato.altura / 2))
                        cor_corpo = (0.5, 0.5, 0.55, 1)
                        cor_bico = (0.6, 0.3, 0.1, 1)

                    Color(0, 0, 0, 0.25)
                    Ellipse(pos=(p_x + 5, p_y - 25), size=(pato.largura * 0.8, 12))

                    Color(cor_corpo[0]*0.6, cor_corpo[1]*0.6, cor_corpo[2]*0.6, 1)
                    Ellipse(pos=(p_x, p_y - 2), size=(pato.largura, pato.altura))
                    Color(*cor_corpo)
                    Ellipse(pos=(p_x, p_y), size=(pato.largura, pato.altura))

                    fx_cabeca = p_x + (pato.largura * 0.7) if olhando_direita else p_x - (pato.tamanho_cabeca * 0.3)
                    fy_cabeca = p_y + (pato.altura * 0.4)

                    Color(cor_corpo[0]*0.6, cor_corpo[1]*0.6, cor_corpo[2]*0.6, 1)
                    Ellipse(pos=(fx_cabeca, fy_cabeca - 1), size=(pato.tamanho_cabeca, pato.tamanho_cabeca))
                    Color(*cor_corpo)
                    Ellipse(pos=(fx_cabeca, fy_cabeca), size=(pato.tamanho_cabeca, pato.tamanho_cabeca))

                    Color(*cor_bico)
                    fx_bico = fx_cabeca + (pato.tamanho_cabeca * 0.8) if olhando_direita else fx_cabeca - (pato.tamanho_cabeca * 0.4)
                    fy_bico = fy_cabeca + (pato.tamanho_cabeca * 0.2)
                    Ellipse(pos=(fx_bico, fy_bico), size=(pato.tamanho_cabeca * 0.6, pato.tamanho_cabeca * 0.4))

                    if pato.vivo:
                        Color(1, 1, 1, 1)
                        fx_olho = fx_cabeca + (pato.tamanho_cabeca * 0.6) if olhando_direita else fx_cabeca + (pato.tamanho_cabeca * 0.2)
                        fy_olho = fy_cabeca + (pato.tamanho_cabeca * 0.5)
                        Ellipse(pos=(fx_olho, fy_olho), size=(6, 6))

                        Color(0, 0, 0, 1)
                        pupila_offset = 2 if olhando_direita else 0
                        Ellipse(pos=(fx_olho + pupila_offset, fy_olho + 1), size=(3, 3))

                        fase_asa = math.sin(tempo * pato.velocidade_asa * math.pi * 2) if not self.em_contagem else 0
                        
                        largura_asa = pato.largura * 0.65
                        altura_asa = pato.altura * 0.75
                        asa_x = p_x + (pato.largura * 0.15)
                        asa_y = p_y + (pato.altura * 0.2) + (fase_asa * 8)

                        PushMatrix()
                        angulo_asa = -20 + (fase_asa * 30)
                        if not olhando_direita:
                            angulo_asa = -angulo_asa

                        Rotate(angle=angulo_asa, origin=(asa_x + largura_asa / 2, asa_y + altura_asa / 2))
                        
                        Color(1, 0.9, 0.2, 1)
                        Ellipse(pos=(asa_x, asa_y), size=(largura_asa, altura_asa))
                        PopMatrix()
                    else:
                        Color(0.3, 0.3, 0.35, 1)
                        Ellipse(pos=(p_x + pato.largura * 0.2, p_y + pato.altura * 0.1), size=(pato.largura * 0.6, pato.altura * 0.5))

                    PopMatrix()


class JogoCidadeNoturnaApp(App):
    def build(self):
        return JogoCidadeNoturnaPatos()


if __name__ == "__main__":
    os.environ["KIVY_NO_ARGS"] = "1"
    JogoCidadeNoturnaApp().run()
