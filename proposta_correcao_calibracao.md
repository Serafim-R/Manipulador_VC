# Análise e Proposta de Correção: Captura de Imagens na Calibração

## 1. O que está acontecendo atualmente?

Há dois motivos diretamente ligados para as imagens estarem saindo iguais e para a câmera não estar se comportando como você deseja:

1. **A câmera estava ficando aberta o tempo todo:**
   No arquivo `backend/app_controller.py`, o método `_rodar_captura_calibracao` abria a câmera antes do loop começar (`self.camera.start()`) e só a fechava no final de toda a rotina (`finally: self.camera.close()`).

2. **Buffer represado do OpenCV / V4L2 (Linux):**
   Quando a câmera permanece aberta e transmitindo a 30 FPS, o driver do Linux (V4L2) mantém uma fila/buffer interno de frames (geralmente uma fila circular FIFO de 4 a 5 frames). 
   Como o robô leva de 5 a 15 segundos se movendo entre uma posição e outra sem que nada leia a câmera nesse intervalo, a fila fica cheia de frames antigos. Quando o robô para e chama `cap.read()` **apenas uma vez**, o OpenCV não entrega o frame do momento presente, mas sim o frame mais antigo que estava guardado na fila.
   Como resultado, você acaba gravando repetidamente frames atrasados tirados antes de o robô terminar o movimento ou até da posição anterior.

---

## 2. O que deve ser feito para corrigir?

1. **Não abrir a câmera no início da rotina:**
   O manipulador deve iniciar o movimento com a câmera completamente desligada/fechada.

2. **Abrir e fechar a câmera pontualmente em cada parada:**
   Assim que o robô atingir cada posição do semicírculo e parar:
   - Abre a câmera (`cv2.VideoCapture(0)`).
   - **Descarta alguns frames de aquecimento (*warmup*, ex: 5 frames):**
     *Importante:* Toda vez que uma câmera USB é aberta, o sensor físico leva frações de segundo para calibrar auto-exposição (AE), ganho e balanço de branco. Ler e descartar cerca de 5 frames limpa o buffer inicial e garante que a foto saia nítida, com iluminação correta e 100% atualizada para aquela posição.
   - Salva a foto na pasta `capturas/`.
   - Fecha e libera a câmera imediatamente (`cap.release()`).

3. **O robô vai para o próximo ponto com a câmera fechada**, repetindo o ciclo.

---

## 3. Detalhamento das modificações propostas

### Arquivo 1: `backend/camera/camera_manager.py`
Adicionar um método `capture_frame(warmup_frames=5)` que encapsula o ciclo de vida pontual: **abre -> descarta warmup -> captura frame válido -> fecha e libera**:

```python
    def capture_frame(self, warmup_frames=5):
        """
        Abre a câmera pontualmente, descarta frames de warmup
        para estabilização de exposição/foco, retorna o frame válido
        e fecha a câmera imediatamente.
        """
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

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None  # Garante que o estado seja resetado
```

---

### Arquivo 2: `backend/app_controller.py`
Na rotina de calibração, remover a abertura prévia contínua da câmera e passar a instância do gerenciador de câmera para o robô:

```python
    def _rodar_captura_calibracao(self):
        # A câmera NÃO é aberta aqui — ela será aberta e fechada
        # pontualmente pelo robô em cada posição do semicírculo.
        self.robot.rotina_captura_calibracao(camera=self.camera)
```

---

### Arquivo 3: `robot_control.py`
Na função `rotina_captura_calibracao`:
Substituir o parâmetro `cap` por `camera=None` e alterar o bloco de captura para capturar com descarte de warmup e fechamento pontual a cada pose:

```python
    def rotina_captura_calibracao(self, camera=None):
        u = np.array([1, 0, 0])
        v = np.array([0, 0, 1])

        b = np.array([-137, 645, 25])
        c = np.array([-300, 210, 0])  
        c -= b

        px, py, pz = sc.calc_semi_circ(c, u, v)

        for i in range(4, 10):
            P_atual = np.array([px[i], py[i], pz[i]])
            P_proximo = np.array([px[i+1], py[i+1], pz[i+1]])
            x, y, z = ik.calculo_angulos(px[i], py[i], pz[i])
            
            # Cálculo de orientação e cinemática inversa
            Z_e = c - P_atual
            Z_hat = Z_e / np.linalg.norm(Z_e)
            v_e = P_proximo - P_atual
            Y_e = v_e - np.dot(v, Z_hat) * Z_hat
            Y_hat = Y_e / np.linalg.norm(Y_e)
            X_hat = np.cross(Y_hat, Z_hat)
            X_hat = X_hat / np.linalg.norm(X_hat)
            
            R_matrix = np.column_stack((X_hat, Y_hat, Z_hat))
            A, B, C = ik.calculo_angulos_abc_semi_circ(R_matrix, P_atual)
            C = 0
            self.enviar_juntas(x, y, z, A, B, C)
            
            # Tempo para o manipulador chegar na pose e estabilizar
            if i == 4:
                time.sleep(15)
            else:
                time.sleep(5)

            # === CAPTURA PONTUAL: Abre, captura com warmup e fecha ===
            print(f"Capturando imagem na posição {i}...")
            if camera is not None:
                frame = camera.capture_frame(warmup_frames=5)
            else:
                # Fallback caso rode o arquivo avulso sem app_controller
                cap = cv2.VideoCapture(0)
                frame = None
                if cap.isOpened():
                    for _ in range(5):
                        ret, f = cap.read()
                        if ret:
                            frame = f
                    cap.release()

            if frame is not None:
                os.makedirs("capturas", exist_ok=True)
                nome_arquivo = f"pos(x={px[i]:.2f}__y={py[i]:.2f}__z={pz[i]:.2f}).jpg"
                caminho_arquivo = os.path.join("capturas", nome_arquivo)
                sucesso = cv2.imwrite(caminho_arquivo, frame)
                if sucesso:
                    print(f"Imagem salva com sucesso como {caminho_arquivo}")
                else:
                    print(f"Erro: OpenCV falhou ao salvar {caminho_arquivo}")
            else:
                print("Erro: Falha ao capturar imagem da câmera.")

        self.enviar_juntas(0, 0, 0, 0, 0, 0)
```
