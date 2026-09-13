readme_content = """# Vertex Intelligence Core (VIC) — Vertex MCP Bible

**VIC (Vertex Intelligence Core)** es un sistema modular, seguro y 100% autónomo basado en el protocolo **MCP (Model Context Protocol)** y orquestado con **LangGraph**. Diseñado específicamente para operaciones de *Red Teaming*, automatización de ciberseguridad y auditoría de infraestructura bajo un esquema *air-gapped* (local).

---

## **Arquitectura del Ecosistema**

El sistema opera a través de microservicios aislados en contenedores Docker, comunicados mediante una red interna segura y coordinados por un motor de razonamiento neuronal local.

| Componente | Rol Táctico | Tecnología Base |
| :--- | :--- | :--- |
| **`mcp-api-gateway`** | Enrutamiento perimetral de tráfico | Traefik v3.0 |
| **`mcp-recon`** | Escaneo de superficie de red y puertos | Python / Uvicorn / Nmap |
| **`mcp-vector`** | Memoria persistente y RAG local | ChromaDB / Docker Volumes |
| **`mcp-infra`** | Auditoría de seguridad en contenedores | Docker SDK / Psutil / Socat |
| **`mcp-orchestrator`** | Orquestación multi-agente y síntesis | LangGraph / LangChain / Gemma 4 |

---

## **Las Trincheras: Desafíos Técnicos Superados**

El desarrollo de VIC en un entorno Windows con Docker Desktop no estuvo exento de combates cerrados contra restricciones de sistema:

1. **Choque de Permisos en Volúmenes de Windows (`SQLite OperationalError`):**
   * *El Problema:* Al montar directorios físicos de Windows en contenedores Linux con usuarios restringidos (`vertex_mcp`), ChromaDB fallaba al abrir la base de datos por falta de permisos de escritura.
   * *La Solución:* Migración a volúmenes nativos gestionados por Docker e inyección de la asignación de dueños (`chown`) en tiempo de *build* dentro del Dockerfile antes de degradar privilegios.

2. **Infiltración del Socket de Docker en Windows (WSL2):**
   * *El Problema:* Docker Desktop protege celosamente el acceso a `/var/run/docker.sock`, bloqueando los cambios de permisos o de grupo secundarios desde contenedores sin privilegios.
   * *La Solución:* Implementación de un **Puente Socat (TCP Proxy)**. Un proceso maestro inicializa un túnel interno redirigiendo el socket protegido a un puerto TCP local (`127.0.0.1:2375`), permitiendo que el microservicio de infraestructura consuma la API de Docker de forma segura y sin ser `root`.

3. **Orquestación Multi-Agente con LangGraph & LLM Local:**
   * *El Problema:* Fusionar telemetría de red estructurada (Nmap), contexto recuperado por vectores (ChromaDB) y auditorías de contenedores sin exponer datos a APIs de la nube.
   * *La Solución:* Conexión de LangChain a **LM Studio** corriendo **Gemma 4** localmente a través de `host.docker.internal:1234`, logrando razonamiento deductivo de élite con cumplimiento normativo y privacidad absoluta.

---

## **Flujo de Ejecución del Grafo**

"""