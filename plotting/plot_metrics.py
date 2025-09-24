import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def plot_metrics_one_pass(model_name:str = "lei", metrics_path:str = "../metrics/"):
    
    full_data = pd.DataFrame()

    for filename in os.listdir(metrics_path):
        if filename.startswith(model_name):
            full_name = os.path.join(metrics_path, filename)
            data_frame = pd.read_csv(full_name)
            overall_vals = data_frame[data_frame["file"]=="OVERALL"].copy(deep=True)
            strategy = filename.split("metrics_")[1][:-4]
            overall_vals["prompt_st"] = [strategy]*len(overall_vals)
            
            full_data = pd.concat([full_data, overall_vals], ignore_index=True)
    
    full_data.drop(columns=["file"],inplace=True)
    full_data["prompt_st"] = full_data["prompt_st"].replace("output", "zero_shot")
    
    sns.set_style('ticks')
    sorted_columns = full_data["prompt_st"].unique().sort()
    plot = sns.barplot(data=full_data, x="prompt_st", y="f1_score", hue="field", order=sorted_columns)
    plot.set_xlabel("Prompt strategy", fontsize=18)
    plot.set_ylabel("F1 Score", fontsize=18)
    plt.legend(loc='upper right', bbox_to_anchor=(1,1.2), title="Extracted field")
    plt.tight_layout()
    plt.savefig(model_name+"_metrics_2_pass.png",dpi=600)

plot_metrics_one_pass(model_name="llama", metrics_path="../metrics_2pass/")