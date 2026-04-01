# UNET Better X

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2.x-0C4B33?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active%20Development-0A7E8C)
![Architecture](https://img.shields.io/badge/Architecture-Monolith%20MVC-1F2937)

Plataforma social web inspirada en Twitter/X, desarrollada con Django, enfocada en experiencia de usuario, arquitectura clara y buenas practicas de backend.

English summary: UNET Better X is a Django-based social platform inspired by Twitter/X, featuring authentication, publishing, social graph, mentions, and direct messaging.

## Indice (ES)

1. [Resumen ejecutivo](#resumen-ejecutivo)
2. [Demostracion funcional](#demostracion-funcional)
3. [Stack tecnologico](#stack-tecnologico)
4. [Arquitectura del proyecto](#arquitectura-del-proyecto)
5. [Instalacion y ejecucion](#instalacion-y-ejecucion)
6. [Variables de entorno](#variables-de-entorno)
7. [Calidad y seguridad](#calidad-y-seguridad)
8. [Roadmap](#roadmap)
9. [Autor](#autor)

## Index (EN)

1. [Executive summary](#executive-summary)
2. [Feature demo](#feature-demo)
3. [Technology stack](#technology-stack)
4. [Project architecture](#project-architecture)
5. [Setup and run](#setup-and-run)
6. [Environment variables](#environment-variables)
7. [Quality and security](#quality-and-security)
8. [Roadmap](#roadmap-en)
9. [Author](#author)

---

## Resumen ejecutivo

UNET Better X implementa el ciclo principal de una red social moderna:

- Autenticacion de usuarios (registro, login, logout).
- Publicacion de contenido con texto e imagen.
- Feed personalizado con paginacion.
- Sistema social de follow/unfollow.
- Likes y retweets.
- Menciones por username y sistema de mensajes directos.
- Perfil editable con biografia e imagen.

Objetivo profesional: demostrar dominio de Django en modelado relacional, vistas basadas en funcion y clase, optimizacion de consultas y estructura mantenible para evolucionar a produccion.

## Demostracion funcional

Flujos principales cubiertos por la aplicacion:

- Onboarding: registro de usuario y acceso autenticado.
- Engagement: crear, editar, eliminar y republicar posts.
- Social graph: seguir/dejar de seguir usuarios y explorar perfiles.
- Interaction layer: likes, menciones y mensajeria privada.
- Profile management: actualizacion de datos personales e imagen de perfil.

## Stack tecnologico

Tecnologias nucleares utilizadas en esta aplicacion:

- Backend framework: Django 5.2.x
- Lenguaje: Python 3.10+
- Base de datos: PostgreSQL (via psycopg2-binary)
- Templates: Django Templates
- Frontend base: HTML, CSS y JavaScript
- Gestion de archivos: Django Media (uploads de posts y perfiles)
- Configuracion segura: variables de entorno con python-dotenv
- Email transaccional: SMTP con EmailMessage de Django

Dependencias relevantes del proyecto (segun requirements):

- Django
- psycopg2-binary
- python-dotenv
- Pillow
- django-htmx

Nota: el archivo requirements incluye paquetes adicionales de experimentacion. Para despliegue productivo, se recomienda separar dependencias por entorno (dev/prod).

## Arquitectura del proyecto

Estructura principal:

- Twitter/: configuracion global del proyecto (settings, urls, wsgi, asgi)
- Unet/: app principal con modelos, vistas, formularios y rutas
- Unet/templates/twitter/: vistas renderizadas en servidor
- Unet/static/: recursos estaticos (css, js, img)
- media/: contenido subido por usuarios

Modelos clave:

- Profile: extension 1:1 de User
- Post: publicaciones y retweets
- Like: relacion usuario-post con restriccion unica
- Relationship: follow graph entre usuarios
- DirectMessage: mensajeria privada
- Mention: indice de menciones en publicaciones

## Instalacion y ejecucion

### Requisitos

- Python 3.10 o superior
- PostgreSQL en ejecucion
- Git

### 1) Clonar repositorio

```bash
git clone https://github.com/tuusuario/tu-repo.git
cd tu-repo
```

### 2) Crear entorno virtual

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4) Configurar variables de entorno

Crea un archivo .env en la raiz del proyecto (ver seccion siguiente).

### 5) Aplicar migraciones

```bash
python manage.py migrate
```

### 6) Ejecutar servidor local

```bash
python manage.py runserver
```

Abrir en navegador: http://127.0.0.1:8000/

## Variables de entorno

Ejemplo de archivo .env:

```env
SECRET_KEY=tu_secret_key_segura
DEBUG=True

DB_NAME=unetx_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password
```

## Calidad y seguridad

- Uso de relaciones unicas para prevenir duplicados (likes, follows, menciones).
- Manejo de autenticacion con sistema nativo de Django.
- Carga de secretos mediante variables de entorno.
- Estructura orientada a separacion de responsabilidades (models, forms, views, templates).

Mejoras recomendadas para produccion:

- Restringir ALLOWED_HOSTS y DEBUG=False.
- Configurar almacenamiento estatico/media para cloud.
- Añadir CI con pruebas automaticas.
- Integrar colas (Celery) para emails y tareas async.

## Roadmap

- Implementar busqueda avanzada de usuarios y contenido.
- Añadir API REST con Django REST Framework.
- Incorporar tests unitarios y de integracion.
- Mejorar observabilidad (logs estructurados y metricas).

## Logros tecnicos (Recruiter Focus)

Aspectos de ingenieria que elevan este proyecto mas alla de un CRUD basico:

- Modelado relacional robusto con restricciones de unicidad para evitar estados inconsistentes.
- Optimizacion de consultas en feed y perfil usando select_related y prefetch_related.
- Paginacion para mejorar rendimiento y experiencia en timelines con alto volumen.
- Uso de variables de entorno para secretos y configuracion sensible.
- Separacion clara por capas: modelos, formularios, vistas, urls y templates.
- Base preparada para evolucionar a arquitectura API-first sin reescritura completa.

Impacto tecnico esperado:

- Menor latencia en vistas de alto trafico.
- Menor costo de mantenimiento por estructura limpia.
- Menor riesgo operativo por controles de integridad de datos.

## Valor para negocio

- Permite validar rapidamente funcionalidades core de red social.
- Reduce time-to-market para MVP academico o startup.
- Sirve como base reutilizable para features sociales en otros productos.

---

## Executive Summary

UNET Better X showcases a full social-network core built with Django:

- User authentication and onboarding.
- Post creation with media support.
- Personalized timeline and pagination.
- Follow system, likes, retweets, mentions, and direct messages.
- Profile editing and account personalization.

This project is aimed at demonstrating production-minded backend thinking: data modeling, query optimization, secure configuration practices, and maintainable architecture.

## Feature Demo

- Register and log in users.
- Publish, edit, and delete posts.
- Follow and unfollow users.
- Interact via likes, retweets, mentions, and private messages.
- Manage profile photo and bio.

## Technology Stack

- Python 3.10+
- Django 5.2.x
- PostgreSQL
- Django Templates + HTML/CSS/JavaScript
- python-dotenv for environment-based configuration
- SMTP integration for email notifications

## Project Architecture

- Twitter/: project settings and routing
- Unet/: core app (models, forms, views, urls)
- Unet/templates/twitter/: server-rendered templates
- Unet/static/: static assets
- media/: user-uploaded content

## Setup and Run

```bash
git clone https://github.com/tuusuario/tu-repo.git
cd tu-repo
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Environment Variables

Use a .env file for secrets and environment-specific settings.

## Quality and Security

- Relational constraints to avoid duplicate interactions.
- Environment-based secret handling.
- Django authentication and structured application layering.

## Roadmap EN

- Add advanced discovery/search features.
- Expose REST API endpoints.
- Increase test coverage and CI automation.
- Improve production observability.

## Technical Highlights (Recruiter Focus)

Engineering choices that position this project above a basic social CRUD clone:

- Strong relational data design with uniqueness constraints to prevent inconsistent states.
- Query optimization in timeline and profile views through select_related and prefetch_related.
- Pagination strategy to maintain performance under larger content volumes.
- Environment-variable based secret management for safer configuration.
- Clear layered architecture (models, forms, views, urls, templates).
- Solid foundation to evolve toward an API-first architecture.

Expected engineering impact:

- Lower response times on high-traffic screens.
- Better maintainability and onboarding for new developers.
- Reduced operational risk through database-level integrity guarantees.

## Business Value

- Fast validation of core social-network product capabilities.
- Reduced MVP delivery time for academic and startup contexts.
- Reusable base for social features in future digital products.

## Autor

Juan Paredes  
Email: jdpgparedes@gmail.com

## Author

Juan Paredes  
Email: jdpgparedes@gmail.com