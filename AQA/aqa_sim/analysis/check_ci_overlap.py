"""If 95% CIs overlap, you can't claim significant difference.
Verify your comparison claims are actually supported."""

for config in comparisons:
    tps_split = df[(df.protocol=="SplitBFT") & (df.config==config)].tps
    tps_aqa = df[(df.protocol=="AQA-SplitBFT") & (df.config==config)].tps
    
    ci_split = (tps_split.mean() - 1.96*tps_split.sem(), tps_split.mean() + 1.96*tps_split.sem())
    ci_aqa = (tps_aqa.mean() - 1.96*tps_aqa.sem(), tps_aqa.mean() + 1.96*tps_aqa.sem())
    
    overlaps = not (ci_split[1] < ci_aqa[0] or ci_aqa[1] < ci_split[0])
    stat, pvalue = wilcoxon(tps_split, tps_aqa)
    
    print(f"{config}: overlap={overlaps}, p={pvalue:.4f}")
    # In the paper, only claim significance where p < 0.05 AND no overlap