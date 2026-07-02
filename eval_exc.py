import subprocess

tasks = ["tasd", "asqp", "acd"]
pool_sizes = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0"]
dataset_names = ["rest16", "flightabsa", "coursera", "hotels"]
seeds = [42, 43, 44]
modes = ["random", "rag"]

for seed in seeds:
  for dataset_name in dataset_names:
    for task in tasks:
        for pool_size in pool_sizes:
          for mode in modes:
            cmd = [
                "python",
                "eval.py",
                "--task", task,
                "--pool_size", pool_size,
                "--llm", "gemma3:27b",
                "--dataset_name", dataset_name,
                "--seed", str(seed),
                "--mode", str(mode)
            ]
            print("Running:", " ".join(cmd))
            subprocess.run(cmd, check=True)



