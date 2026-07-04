import time, os, json, random, signal, argparse
from services.llm_providers import predict_llm

def timeout_handler(signum, frame):
    raise TimeoutError("Prediction timed out")

args = None

def main():
    parser = argparse.ArgumentParser(description="Evaluation Script")
    parser.add_argument("--task", type=str, required=True, help="Task name, z.B. acd, asqp, etc.")
    parser.add_argument("--llm", type=str, required=True, help="LLM model to use, z.B. gemma3:4b, gemma3:7b, gpt-3.5-turbo, gpt-4")
    parser.add_argument("--pool_size", type=float, default=0.2, help="Proportion of training data to use as pool, e.g., 0.2 for 20%")
    parser.add_argument("--dataset_name", type=str, default="rest16", help="Name of the dataset, z.B. rest16")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--mode", type=str, default="random", help="Type of example retrieval mechanism")
    global args
    args = parser.parse_args()

    print(f"Gewählter Task: {args.task}")

if __name__ == "__main__":
    main()


task = args.task  # "asqp", "acd", "tasd"

if args.mode == "random":
   predictions_str = "predictions_random"
else:
   predictions_str = "predictions"

print("Pool size (type):", type(args.pool_size))
print("Pool size:", args.pool_size)
print("LLM (type):", type(args.llm))
print("LLM:", args.llm)
print("Task (type):", type(args.task))
print("Task:", args.task)
print("Mode:", args.mode)


### Check if file evaluation/predictions/{task}/{llm}/{pool_size}/predictions.json exists
if os.path.exists(f"evaluation/{predictions_str}/seed_{args.seed}/{task}/{args.llm.replace(':', '_')}/{args.pool_size}/{args.dataset_name}/predictions.json"):
    print(f"Predictions for task {task}, llm {args.llm}, pool size {args.pool_size}, dataset {args.dataset_name} already exist. Exiting.")
    exit(0)
else:
    print(f"Predictions for task {task}, llm {args.llm}, pool size {args.pool_size}, dataset {args.dataset_name} do not exist. Continuing.")

if task == "asqp":
   considered_sentiment_elements=["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]
elif task == "acd":
    considered_sentiment_elements=["aspect_category"]
elif task == "tasd":
    considered_sentiment_elements=["aspect_term", "aspect_category", "sentiment_polarity"]

def load_data(dataset_name, split, task):
    examples = []
    task_str = "tasd" if task in ['tasd', 'acd', 'e2e'] else task
    with open(f"evaluation/data/{task_str}/{dataset_name}/{split}.txt", "r", encoding="utf-8") as f:
        for line in f:
            text, aspect_str = line.strip().split("####")
            aspect_list = eval(aspect_str)  # besser wäre ast.literal_eval
            
            if considered_sentiment_elements == ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]:
                aspect_list = [
                    {
                        "aspect_term": aspect[0],
                        "aspect_category": aspect[1],
                        "sentiment_polarity": aspect[2],
                        "opinion_term": aspect[3]
                    }
                    for aspect in aspect_list
                ]
            elif considered_sentiment_elements == ["aspect_category"]:
                aspect_list = [
                    {
                        "aspect_category": aspect[1]
                    }
                    for aspect in aspect_list
                ]
                # remove duplicates in aspect_list
                aspect_list = [dict(t) for t in {tuple(d.items()) for d in aspect_list}]
            elif considered_sentiment_elements == ["aspect_term", "aspect_category", "sentiment_polarity"]:
                aspect_list = [
                    {
                        "aspect_term": aspect[0],
                        "aspect_category": aspect[1],
                        "sentiment_polarity": aspect[2]
                    }
                    for aspect in aspect_list
                ]

            examples.append({
                "text": text,
                "label": aspect_list
            })
    return examples

if task == "asqp":
   allow_implicit_aspect_terms = True
   allow_implicit_opinion_terms = False
elif task == "acd":
    allow_implicit_aspect_terms = False
    allow_implicit_opinion_terms = False
elif task == "tasd":
    allow_implicit_aspect_terms = True
    allow_implicit_opinion_terms = False
    
llm = args.llm
n_few_shot = 10
pool_size = args.pool_size  # 0.2 means 20% of training data as pool

train_data = load_data(args.dataset_name, "train", task)
random.seed(args.seed)
random.shuffle(train_data)
test_data = load_data(args.dataset_name, "test", task)
pool = train_data[:int(1000*pool_size)]
print(f"Using {len(pool)} examples as pool.")

# see list of unique aspect categories. ac is in example["label"][tuple_idx][1]
try:
    ac_set = set()
    for example in train_data + test_data:
        for tuple_idx in range(len(example["label"])):
            ac_set.add(example["label"][tuple_idx]["aspect_category"])
    unique_aspect_categories = list(ac_set)
except KeyError:
    unique_aspect_categories = []


try:    
    pol_set = set()
    for example in train_data + test_data:
        for tuple_idx in range(len(example["label"])):
            pol_set.add(example["label"][tuple_idx]["sentiment_polarity"])
    unique_polarities = list(pol_set)
except KeyError:
    unique_polarities = []

print(unique_aspect_categories)
print(unique_polarities)

predictions = []


for idx, example in enumerate(test_data):
    example["text"] = example["text"].replace('"', "'")  # replace double quotes with single quotes
    text = example['text']
    
    duration = time.time()
    
    print(f"Predicting example {idx+1}/{len(test_data)}: {text}")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    if args.mode == "rag":
        few_shot_pool = pool
    else:
        few_shot_pool = random.sample(pool, 10)
        print("took ", len(few_shot_pool), "examples from pool.")
    try:
      llm_output= predict_llm(
        text,
        considered_sentiment_elements=considered_sentiment_elements,
        examples=few_shot_pool,
        aspect_categories=unique_aspect_categories,
        polarities=unique_polarities,
        allow_implicit_aspect_terms=allow_implicit_aspect_terms,
        allow_implicit_opinion_terms=allow_implicit_opinion_terms,
        n_few_shot=n_few_shot,
        llm_model=llm)[0]
      signal.alarm(0)
    except TimeoutError:
      print("Prediction timed out after 10 seconds")
      llm_output = {"aspects": []}
    except Exception as e:
      print("Error during prediction:", e)
      llm_output = {"aspects": []}
    
    try:
      aspects_out = llm_output["aspects"]
    except:
      aspects_out = []
      
    print(f"Evaluating example {idx+1}/{len(test_data)}: {text}", llm_output, f"took {time.time()-duration:.2f}s", "Gold standard:", example['label'])
    
    predictions.append({"text": text, "predicted": aspects_out, "time": time.time()-duration, "gold": example['label']})

# store predictions in /evaluation/predictions/{task}/{llm}/{pool_size}/predictions.json

# create directory if it does not exist
os.makedirs(f"evaluation/{predictions_str}/seed_{args.seed}/{task}/{llm.replace(':', '_')}/{pool_size}/{args.dataset_name}", exist_ok=True)

# save predictions
with open(f"evaluation/{predictions_str}/seed_{args.seed}/{task}/{llm.replace(':', '_')}/{pool_size}/{args.dataset_name}/predictions.json", "w", encoding="utf-8") as f:
    json.dump(predictions, f, ensure_ascii=False, indent=4)


