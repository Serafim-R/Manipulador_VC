# Registro das Modificações: Rotina de Captura da Calibração

Este documento detalha todas as alterações realizadas no projeto para resolver o problema de imagens duplicadas/atrasadas e atender ao requisito de **manter a câmera fechada durante o deslocamento do robô, abrindo-a apenas pontualmente no momento de cada captura**.

---

## 1. Problemas Identificados e Diagnóstico

1. **Câmera permanentemente aberta durante os movimentos:**
   - Em `backend/app_controller.py`, a função `_rodar_captura_calibracao` executava `self.camera.start()`, mantendo o dispositivo de vídeo (`cv2.VideoCapture`) aberto durante todo o ciclo do manipulador (mais de 45 segundos).
2. **Buffer represado do driver Linux (V4L2 / OpenCV):**
   - O OpenCV no Linux mantém internamente uma fila FIFO circular de buffers (4 a 5 frames). Como a câmera capturava continuamente a 30 FPS mas o código ficava parado em `time.sleep` entre os pontos, o buffer ficava represado com frames antigos.
   - Ao chamar `cap.read()` apenas uma vez em cada pose, o OpenCV retirava da fila um frame registrado segundos antes (da posição anterior ou da pose inicial), gerando **arquivos com conteúdo idêntico**.
3. **Ausência de aquecimento (*warmup*) do sensor na inicialização:**
   - Sensores de câmeras USB necessitam de alguns milissegundos para convergir os algoritmos internos de auto-exposição (AE), ganho e balanço de branco (AWB). Abrir a câmera e ler apenas o primeiro frame pode gerar imagens pretas ou com ruído.

---

## 2. Resumo das Alterações Realizadas

| Arquivo | Modificação Principal |
| :--- | :--- |
| [`backend/camera/camera_manager.py`](file:///home/adilson/Documentos/Serafim/projeto_manipulador/backend/camera/camera_manager.py) | Adicionado método `capture_frame(warmup_frames=5)` com abertura, descarte de warmup, leitura e fechamento imediato; reset de `self.cap = None` no `close()`. |
| [`backend/app_controller.py`](file:///home/adilson/Documentos/Serafim/projeto_manipulador/backend/app_controller.py) | Removida a abertura global da câmera em `_rodar_captura_calibracao()`; repassada a referência `self.camera` para a rotina do robô. |
| [`robot_control.py`](file:///home/adilson/Documentos/Serafim/projeto_manipulador/robot_control.py) | Atualizada a assinatura de `rotina_captura_calibracao(self, camera=None)`; em cada pose, a captura é feita de forma pontual (abre, descarta 5 frames, salva e fecha), sem exibir na interface gráfica. |

---

## 3. Detalhamento por Arquivo (Antes vs. Depois)

### 3.1. `backend/camera/camera_manager.py`

#### Antes:
```python
    def close(self):

        if self.cap:

            self.cap.release()

    def start(self):
```

#### Depois:
```python
    def close(self):

        if self.cap is not None:

            self.cap.release()
            self.cap = None

    def capture_frame(self, warmup_frames=5):

        if not self.open():
            print("Erro: Não foi possível abrir a câmera.")
            return None

        frame = None
        try:
            for _ in range(warmup_frames):
                frame = self.read()
            return frame
        finally:
            self.close()

    def start(self):
```

---

### 3.2. `backend/app_controller.py`

#### Antes:
```python
    def _rodar_captura_calibracao(self):
        
        if not self.camera.start():
            raise RuntimeError("Nao foi possivel abrir a camera")
 
        try:
            self.robot.rotina_captura_calibracao(self.camera.cap)
        finally:
            self.camera.close()
```

#### Depois:
```python
    def _rodar_captura_calibracao(self):

        # A câmera é aberta e fechada pontualmente a cada pose pelo robô
        self.robot.rotina_captura_calibracao(camera=self.camera)
```

---

### 3.3. `robot_control.py`

#### Antes:
```python
    def rotina_captura_calibracao(self, cap):
        # ... cálculo do semicírculo ...
        for i in range(4,10):
            # ... movimentação do robô ...
            self.enviar_juntas(x, y, z, A, B, C)
            if i == 4:
                time.sleep(15)
            else:
                time.sleep(5)
            # === ADICIONAR ESTE BLOCO NO FINAL DA FUNÇÃO ===
            print("Realizando a captura de imagem da calibração...")
            ret, frame = cap.read()

            if ret:
                os.makedirs("capturas", exist_ok=True)
                nome_arquivo = f"pos(x={px[i]:.2f}__y={py[i]:.2f}__z={pz[i]:.2f}).jpg"
                caminho_arquivo = os.path.join("capturas", nome_arquivo)
                sucesso = cv2.imwrite(caminho_arquivo, frame)
                if sucesso:
                    print(f"Imagem salva com sucesso como {caminho_arquivo}")
                else:
                    print(f"Erro: OpenCV falhou ao salvar {caminho_arquivo}")
            else:
                print("Erro: Falha ao ler o frame da câmera já aberta.")
            time.sleep(2)

        self.enviar_juntas(0, 0, 0, 0, 0, 0)
```

#### Depois:
```python
    def rotina_captura_calibracao(self, camera=None):
        # ... cálculo do semicírculo ...
        for i in range(4,10):
            # ... movimentação do robô ...
            self.enviar_juntas(x, y, z, A, B, C)
            if i == 4:
                time.sleep(15)
            else:
                time.sleep(5)

            # Captura pontual: abre a câmera, descarta warmup e fecha logo em seguida
            print(f"Realizando a captura de imagem da calibração (posição {i})...")
            if camera is not None:
                frame = camera.capture_frame(warmup_frames=5)
            else:
                cap = cv2.VideoCapture(0)
                frame = None
                if cap.isOpened():
                    for _ in range(5):
                        ret, f = cap.read()
                        if ret:
                            frame = f
                    cap.release()

            if frame is not None:
                pasta_capturas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas")
                os.makedirs(pasta_capturas, exist_ok=True)
                nome_arquivo = f"pos(x={px[i]:.2f}__y={py[i]:.2f}__z={pz[i]:.2f}).jpg"
                caminho_arquivo = os.path.join(pasta_capturas, nome_arquivo)
                sucesso = cv2.imwrite(caminho_arquivo, frame)
                if sucesso:
                    print(f"Imagem salva com sucesso como {caminho_arquivo}")
                else:
                    print(f"Erro: OpenCV falhou ao salvar {caminho_arquivo}")
            else:
                print("Erro: Falha ao capturar frame da câmera.")
            time.sleep(1)

        self.enviar_juntas(0, 0, 0, 0, 0, 0)
```

---

## 4. Novo Fluxo Operacional

```
[Clique em "Calibrar" na Interface]
                  │
                  ▼
[Inicia RobotActionThread (não trava interface)]
                  │
                  ▼
         [Câmera FECHADA]
                  │
  ┌───────────────┴─────────────────────────────┐
  │ Loop: poses i = 4 até 9                     │
  │  1. Robô move para pose i                   │
  │  2. Aguarda estabilização (15s ou 5s)       │
  │  3. Abre câmera (cv2.VideoCapture(0))       │
  │  4. Lê e descarta 5 frames de warmup        │
  │  5. Captura frame atual e salva em disco    │
  │  6. FECHA câmera imediatamente (release)    │
  │  7. Repete para próxima pose...             │
  └───────────────┬─────────────────────────────┘
                  │
                  ▼
      [Robô retorna a Home (0,0,0,0,0,0)]
                  │
                  ▼
         [Fim da Calibração]
```

---

## 5. Verificação Realizada
- Compilação estática de sintaxe executada via `python -m py_compile` em todos os arquivos modificados.
- Teste de consistência do caminho absoluto para garantir a gravação na pasta `capturas/` do projeto.
