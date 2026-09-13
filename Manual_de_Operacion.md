**MANUAL DE OPERACIÓN: VERTEX INTELLIGENCE CORE (VIC v3.0)**
*Propietario:* Denis Sanchez Leyva | CEO, Vertex Coders LLC (Miami)

*Objetivo:* Guía operativa para el arranque, ejecución de misiones multi-agente, auditoría de infraestructura y remediación activa del ecosistema VIC.

---

**1. Requisitos Previos y Entorno**
Antes de desplegar el núcleo, asegúrate de cumplir con los siguientes requisitos en tu máquina de desarrollo (Windows con WSL2 o Linux):

* **Docker Desktop** activo y configurado con soporte para sockets.
* **LM Studio** ejecutándose en el host local, sirviendo el modelo **Gemma 4** en el puerto `1234` con la API compatible activada (`http://localhost:1234`).
* Estructura de directorios base establecida en `G:\vertex-mcp-bible` (o tu ruta de trabajo local).

---

**2. Despliegue de la Flota (Los 5 Nodos)**
Para levantar todo el ecosistema de microservicios aislados y la red segura interna, utiliza la secuencia de comandos Docker oficial:

```cmd
cd infra
docker-compose up -d --build

```

**Verificación de contenedores activos:**
Ejecuta el script de pruebas de infraestructura para comprobar que los 5 nodos principales y el puente Socat responden correctamente:

```cmd
cd ..
python test_infra.py

```

*Resultado esperado:* Listado JSON con la telemetría del host (psutil) y el estado de seguridad de los contenedores (`mcp-recon`, `mcp-vector`, `mcp-orchestrator`, `mcp-infra`, `mcp-harden`).

---

**3. Ejecución de Misiones Tácticas (Orquestación LangGraph)**
Para lanzar una misión completa donde VIC escanee una red, consulte la memoria vectorial corporativa, audite los contenedores y genere un informe táctico mediante Gemma, ejecuta:

```cmd
python test_orchestrator.py

```

*¿Qué ocurre internamente?*

1. El nodo **`mcp-recon`** escanea la superficie del objetivo (`127.0.0.1`).
2. El nodo **`mcp-vector`** recupera el contexto semántico e identidad corporativa de Vertex Coders desde ChromaDB.
3. El nodo **`mcp-infra`** interroga al demonio Docker vía Socat para detectar riesgos de privilegios.
4. El nodo **`mcp-orchestrator`** procesa todo a través de LangGraph y alimenta el LLM local.
5. Se genera un **Reporte Táctico en Markdown** detallado listo para la toma de decisiones.

---

**4. Generación de Parches de Hardening Automático**
Si necesitas que VIC analice una imagen insegura o genere directrices de autodefensa basadas en el Principio de Menor Privilegio (PoLP):

1. Configura el objetivo en el script de pruebas de remediación (`test_harden.py`).
2. Ejecuta la petición RPC contra el Nodo 05:
```cmd
python test_harden.py

```


3. El sistema devolverá un `Dockerfile` optimizado con la creación obligatoria de usuarios no privilegiados (`vertex_secure_user`), control de dueños y restricciones de kernel.

---

**5. Protocolo de Apagado y Limpieza**
Para detener las operaciones de forma segura liberando recursos de red y sockets:

```cmd
cd infra
docker-compose down

```

