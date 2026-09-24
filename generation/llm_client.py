"""
llm_client.py
=============
Client LLM unique avec 3 backends, sélectionnés via la variable d'env LLM_MODE :

  - "mock"      : mode démo, sans aucune clé API. Génère un paragraphe
                  déterministe à partir d'un template Python qui n'utilise
                  QUE les valeurs du tableau source (donc toujours vérifiable).
                  C'est le mode par défaut, pour que le projet tourne "out of
                  the box" pour un reviewer sans accès à un LLM.
  - "ollama"    : appel à un modèle Llama tournant EN LOCAL via Ollama
                  (https://ollama.com). Aucune clé API, aucun coût : seul
                  prérequis, avoir Ollama installé et un modèle téléchargé.
                  Le modèle exact est choisi via la variable d'env
                  OLLAMA_MODEL (voir .env.example) — typiquement
                  `llama3.2:3b` (bon compromis) ou `llama3.2:1b` (plus léger,
                  pour une machine modeste).
  - "dataiku"   : appelle un LLM connecté via LLM Mesh dans Dataiku.
                  Nécessite de tourner dans un notebook/recipe Dataiku, avec
                  un LLM_ID configuré dans le projet (voir .env.example).

Dans les 3 cas, l'interface exposée est la même : LLMClient.complete(system, user) -> str
"""

import os


class LLMClient:
    def __init__(self, mode: str = None):
        self.mode = mode or os.environ.get("LLM_MODE", "mock")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if self.mode == "dataiku":
            return self._complete_dataiku(system_prompt, user_prompt)
        elif self.mode == "ollama":
            return self._complete_ollama(system_prompt, user_prompt)
        elif self.mode == "mock":
            return self._complete_mock(system_prompt, user_prompt)
        else:
            raise ValueError(f"LLM_MODE inconnu : {self.mode} (attendu : mock / ollama / dataiku)")

    # ------------------------------------------------------------------
    # Backend 1 : Dataiku LLM Mesh
    # ------------------------------------------------------------------
    def _complete_dataiku(self, system_prompt: str, user_prompt: str) -> str:
        """
        Appel via LLM Mesh, à exécuter DANS Dataiku (recipe Python ou notebook).

        NB : l'API exacte de dataikuapi.dss.llm peut varier selon la version
        de Dataiku. Le squelette ci-dessous suit le pattern standard
        (project.get_llm -> new_completion -> with_message -> execute) documenté
        par Dataiku pour LLM Mesh ; vérifier la signature précise dans la
        documentation de votre instance avant mise en prod.
        """
        import dataiku

        llm_id = os.environ.get("DATAIKU_LLM_ID")
        if not llm_id:
            raise EnvironmentError("DATAIKU_LLM_ID non défini (voir .env.example).")

        client = dataiku.api_client()
        project = client.get_default_project()
        llm = project.get_llm(llm_id)

        completion = llm.new_completion()
        completion.with_message(system_prompt, role="system")
        completion.with_message(user_prompt, role="user")

        resp = completion.execute()
        if not resp.success:
            raise RuntimeError(f"Échec de l'appel LLM Mesh : {resp}")
        return resp.text.strip()

    # ------------------------------------------------------------------
    # Backend 2 : Ollama (Llama en local, sans clé API)
    # ------------------------------------------------------------------
    def _complete_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """
        Appelle un modèle local via Ollama (serveur HTTP local, par défaut
        http://localhost:11434). Aucune clé API, aucun coût : seul prérequis,
        avoir Ollama installé (https://ollama.com/download) et un modèle
        téléchargé au préalable, par exemple :

            ollama pull llama3.2:3b        # ~2 Go, bon compromis (défaut)
            ollama pull llama3.2:1b        # ~1.3 Go, machine plus modeste

        Variables d'environnement (voir .env.example) :
          - OLLAMA_HOST     (défaut : http://localhost:11434)
          - OLLAMA_MODEL    (défaut : llama3.2:3b)
          - OLLAMA_TIMEOUT  (défaut : 300 secondes — le premier appel peut être
            lent le temps qu'Ollama charge le modèle en mémoire ; les appels
            suivants sont généralement plus rapides)
        """
        import json
        import socket
        import urllib.request
        import urllib.error

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
        timeout = int(os.environ.get("OLLAMA_TIMEOUT", "300"))

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        req = urllib.request.Request(
            f"{host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            # Erreurs à l'établissement de la connexion (Ollama non lancé,
            # mauvais port, DNS...). urllib enveloppe ces erreurs dans URLError.
            raise ConnectionError(
                f"Impossible de joindre Ollama sur {host}. Vérifiez qu'Ollama "
                f"est bien lancé (`ollama serve`, ou l'application Ollama "
                f"ouverte) et qu'un modèle est disponible (`ollama pull {model}`). "
                f"Erreur d'origine : {e}"
            )
        except (TimeoutError, socket.timeout) as e:
            # NB : contrairement aux erreurs de connexion, un timeout survenant
            # PENDANT la lecture de la réponse (le modèle met trop de temps à
            # répondre) n'est PAS enveloppé dans URLError par urllib — il faut
            # donc l'intercepter séparément, sans quoi il remonte brut.
            raise TimeoutError(
                f"Ollama n'a pas répondu dans le délai imparti ({timeout}s) avec le "
                f"modèle '{model}'. Le tout premier appel peut être lent le temps "
                f"qu'Ollama charge le modèle en mémoire (surtout sur CPU) : "
                f"réessayez une seconde fois, augmentez OLLAMA_TIMEOUT dans .env, "
                f"ou utilisez le modèle plus léger llama3.2:1b (OLLAMA_MODEL=llama3.2:1b). "
                f"Erreur d'origine : {e}"
            )

        contenu = data.get("message", {}).get("content", "")
        if not contenu:
            raise RuntimeError(f"Réponse Ollama inattendue (pas de contenu) : {data}")
        return contenu.strip()

    # ------------------------------------------------------------------
    # Backend 3 : mode démo déterministe (pas de clé API nécessaire)
    # ------------------------------------------------------------------
    def _complete_mock(self, system_prompt: str, user_prompt: str) -> str:
        """
        Simule une génération LLM de façon déterministe, en extrayant les
        couples (nom_indicateur, valeur, unité, variation) directement du
        prompt utilisateur (qui contient le tableau de données), pour
        produire un paragraphe qui n'utilise QUE des valeurs source.

        Ce mode sert de démonstrateur fonctionnel sans dépendance à une API
        externe. Il n'a pas la qualité rédactionnelle d'un vrai LLM, mais il
        respecte scrupuleusement les contraintes anti-hallucination, ce qui
        permet de tester tout le reste du pipeline (vérification, dashboard,
        export) sans clé API.
        """
        import re

        lignes = re.findall(
            r"- (.+?) : ([\d.,]+)\s*(\S+)(?: \(variation vs .+? : ([+-]?[\d.,]+)%\))?",
            user_prompt,
        )
        if not lignes:
            return ("Les indicateurs de cette section n'ont pas pu être formatés "
                    "automatiquement en mode démo ; utilisez LLM_MODE=ollama "
                    "pour une génération complète.")

        phrases = []
        for nom, valeur, unite, variation in lignes:
            phrase = f"L'indicateur « {nom} » s'établit à {valeur} {unite}"
            if variation:
                sens = "en hausse" if not variation.startswith("-") else "en baisse"
                phrase += f", {sens} de {variation.lstrip('+-')}% par rapport à l'exercice précédent"
            phrase += "."
            phrases.append(phrase)

        intro = "Sur l'exercice concerné, NordTech Industries présente les résultats suivants pour cette section. "
        return intro + " ".join(phrases)
