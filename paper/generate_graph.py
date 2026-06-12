import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# Create figure and axis objects with subplots()
fig, ax1 = plt.subplots(figsize=(10, 6))

cycles = list(range(1, 11))
kappa = [0.9371, 0.8809, 0.9019, 0.9062, 0.9182, 0.9222, 0.9181, 0.9100, 0.9312, 0.9851]
agreement = [93.1, 90.0, 90.6, 88.7, 96.3, 95.6, 96.3, 90.0, 90.0, 95.6]

# Try to use a Korean font if available, else default
if os.path.exists('/System/Library/Fonts/AppleGothic.ttf'):
    plt.rc('font', family='AppleGothic')
elif os.path.exists('/Library/Fonts/Arial Unicode.ttf'):
    plt.rc('font', family='Arial Unicode MS')

ax1.set_xlabel('Cycle', fontsize=12)
ax1.set_ylabel(r'Fleiss $\kappa$ (Reliability)', color='tab:blue', fontsize=12)
line1 = ax1.plot(cycles, kappa, color='tab:blue', marker='o', linewidth=2, label=r'Fleiss $\kappa$')
ax1.tick_params(axis='y', labelcolor='tab:blue')
ax1.set_xticks(cycles)
ax1.set_ylim(0.85, 1.0)
ax1.grid(True, linestyle='--', alpha=0.6)

# Instantiate a second axes that shares the same x-axis
ax2 = ax1.twinx()  
ax2.set_ylabel('Reference Standard Agreement (%)', color='tab:red', fontsize=12)
line2 = ax2.plot(cycles, agreement, color='tab:red', marker='s', linewidth=2, label='Agreement (%)')
ax2.tick_params(axis='y', labelcolor='tab:red')
ax2.set_ylim(85, 100)

# Add legends
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='lower right', fontsize=10)

plt.title('Autonomous Evolution of Grading Reliability and Reference Standard Agreement', fontsize=14, pad=15)
fig.tight_layout()  # otherwise the right y-label is slightly clipped

# Save figure
output_path = '/Users/home/vaults/projects/Rubric/paper/figure_2.png'
plt.savefig(output_path, dpi=300)
print(f"Saved graph to {output_path}")
