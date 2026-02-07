This repository holds still evolving the implementation of process design kit of IHP SG13G2 Process Node for Revolution EDA. 
It includes the front-end schematics for all IHP devices (imported from their Xschem implementation) and some parametric layout cells
for the physical layout cells.

Both instance callbacks and layout parametric cells are implemented in Python. Thus, Revolution EDA PDKs are not compatible with OpenPDKs.
At the moment, PDK includes design rule check with headless KLayout using IHP design rule decks. 
Revolution EDA will parse KLayout generated DRC output and will create a table of errors as well as pointing their location on the layout.
<img width="1831" height="1021" alt="Screenshot_2026-02-05_20-01-36" src="https://github.com/user-attachments/assets/5339ef78-bc5a-43fc-b7e0-a984c178821c" />

A similar LVS implementation will be offered shortly.
