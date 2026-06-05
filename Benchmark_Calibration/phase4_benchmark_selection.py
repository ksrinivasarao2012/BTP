import os
import pandas as pd

def run_phase4():
    print("Loading results from previous phases...")
    
    try:
        phase1_df = pd.read_csv('results/phase1/phase1_results.csv')
    except FileNotFoundError:
        print("Error: results/phase1/phase1_results.csv not found.")
        return
        
    try:
        phase2_df = pd.read_csv('results/phase2/phase2_results.csv')
    except FileNotFoundError:
        print("Error: results/phase2/phase2_results.csv not found.")
        return
        
    try:
        phase3_df = pd.read_csv('results/phase3/phase3_results.csv')
    except FileNotFoundError:
        print("Error: results/phase3/phase3_results.csv not found.")
        return
        
    os.makedirs('reports', exist_ok=True)
    
    # We only care about configurations that survived to phase 3
    final_df = phase3_df.copy()
    
    # Merge Phase 1 metrics
    final_df = pd.merge(
        final_df, 
        phase1_df[['Width', 'Height', 'Density', 'd_min', 'Reachability_Rate', 'Mean_Tortuosity']], 
        on=['Width', 'Height', 'Density', 'd_min'], 
        how='left'
    )
    
    # Merge Phase 2 metrics
    final_df = pd.merge(
        final_df, 
        phase2_df[['Width', 'Height', 'Density', 'd_min', 'Collision_Rate']], 
        on=['Width', 'Height', 'Density', 'd_min'], 
        how='left'
    )
    
    # Calculate advanced holistic difficulty score
    # Composite_Score = Reachability_Rate + 0.25 * Mean_Tortuosity - Collision_Rate - Difficulty_Spread - abs(Mean_Drone_Success_Rate - 0.5)
    final_df['Composite_Score'] = (
        final_df['Reachability_Rate'] 
        + 0.25 * final_df['Mean_Tortuosity'] 
        - final_df['Collision_Rate'] 
        - final_df['Difficulty_Spread'] 
        - abs(final_df['Mean_Drone_Success_Rate'] - 0.5)
    )
    
    final_df = final_df.sort_values(by='Composite_Score', ascending=False)
    
    final_df.to_csv('results/final_rankings.csv', index=False)
    
    # Generate report
    report_path = 'reports/final_benchmark_selection.txt'
    with open(report_path, 'w') as f:
        f.write("Final Benchmark Configuration Selection\n")
        f.write("=========================================\n\n")
        
        f.write("Note: Composite_Score is a heuristic ranking metric used only\n")
        f.write("for final candidate ordering and not as a rigorous scientific metric.\n\n")
        
        f.write(f"Total Final Candidates: {len(final_df)}\n\n")
        
        cols = [
            'Width', 'Density', 'd_min', 
            'Reachability_Rate', 'Mean_Tortuosity', 
            'Mean_Drone_Success_Rate', 'Mean_Episode_Success_Rate', 'Collision_Rate', 
            'Difficulty_Spread', 'Composite_Score'
        ]
        available_cols = [c for c in cols if c in final_df.columns]
        
        f.write(final_df[available_cols].to_string(index=False))
        
        f.write("\n\nRecommendation:\n")
        if not final_df.empty:
            best = final_df.iloc[0]
            f.write("The optimally balanced benchmark configuration is:\n")
            f.write(f"Arena Size: {best['Width']}x{best['Height']}\n")
            f.write(f"Density: {best['Density']}\n")
            f.write(f"Minimum Spawn-Goal Distance (d_min): {best['d_min']}\n\n")
            f.write("This configuration offers the best trade-off between physical feasibility, "
                    "sufficient complexity (tortuosity), balanced difficulty (~50% success), "
                    "and repeatable consistency (low spread).\n")
                    
    print(f"Phase 4 complete. Final selection saved to {report_path}")

if __name__ == '__main__':
    run_phase4()
