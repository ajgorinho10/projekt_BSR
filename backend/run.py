import subprocess
import sys
import os

print("=== Menedżer Klastra Bully ===")
nodes_input = "1,2,3,4"

try:
    nodes = [n.strip() for n in nodes_input.split(",")]

    for node_id in nodes:
        port = 8000 + int(node_id)
        print(f"Uruchamianie Węzła {node_id} na porcie {port}...")

        env = os.environ.copy()
        env["NODE_ID"] = str(node_id)

        # Dodajemy 'cmd.exe', '/k' aby okno nie znikało po błędzie!
        subprocess.Popen(
            ["cmd.exe", "/k", sys.executable, "-m", "uvicorn", "nodetest:app", "--port", str(port)],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    print("\nGotowe! Węzły zostały uruchomione w osobnych oknach.")

except Exception as e:
    print(f"Wystąpił błąd: {e}")