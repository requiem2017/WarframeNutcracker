import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
from paddleocr import PaddleOCR
import numpy as np
import requests
import re
import pandas as pd
from fuzzywuzzy import fuzz
import time

ocr = PaddleOCR(lang='ch') 

#pull data from WF market
def getWarframeMarketData(itemsList=[], checkOrder=False, checkItemInfo=False, initialize=None):
    baseUrl = "https://api.warframe.market/v1/items"
    results = {}
    if initialize is not None:
        try:
            response = requests.get(baseUrl, headers={"Language": "zh-hans"})
            if response.status_code == 200:
                data = response.json()
                if 'payload' in data:
                    return data['payload']['items']
            else:
                print(f"Initialization: Error {response.status_code}")
        except Exception as e:
            print(f"Initialization: Request failed - {e}")

    for item in itemsList:
        if checkOrder:
            url = f"{baseUrl}/{item}/orders"
        elif checkItemInfo:
            url = f"{baseUrl}/{item}"
        else:
            return []

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                results[item] = data.get('payload', {})
            else:
                results[item] = f"Error {response.status_code}"
        except Exception as e:
            results[item] = f"Request failed - {e}"

    return results

#Process image, cut image into 4x7 grid
def imageOcr(imagePath, threshold=150):
    ocr = PaddleOCR()
    threshold = 150  
    rows, cols = 4, 7  

    try:
        image = Image.open(imagePath)  
    except FileNotFoundError:
        raise ValueError("Image not found. Check the path.")

    width, height = image.size
    cellWidth = width // cols
    cellHeight = height // rows

    gridGroupedTexts = []

    for row in range(rows):
        for col in range(cols):
            startX = col * cellWidth
            startY = row * cellHeight
            endX = (col + 1) * cellWidth if col != cols - 1 else width
            endY = (row + 1) * cellHeight if row != rows - 1 else height

            section = image.crop((startX, startY, endX, endY))
            sectionArray = np.array(section)

            result = ocr.ocr(sectionArray, cls=True)
            texts = []
            boxes = []
            for line in result[0]:
                box = np.array(line[0], dtype=np.int32)
                text = line[-1][0]
                boxes.append(box)
                texts.append(text)

            groupedTexts = []
            while boxes:
                box = boxes.pop(0)
                text = texts.pop(0)
                group = [(text, box)]
                groupBox = box

                i = 0
                while i < len(boxes):
                    otherBox = boxes[i]
                    distance = np.linalg.norm(np.mean(box, axis=0) - np.mean(otherBox, axis=0))
                    if distance < threshold:
                        group.append((texts.pop(i), otherBox))
                        groupBox = np.vstack((groupBox, otherBox))
                        boxes.pop(i)
                    else:
                        i += 1

                elements = []
                for item in group:
                    elements.append(item[0])

                result = ''.join(elements)
                if 'Prime' in result:
                    groupedTexts.append(result)

            gridGroupedTexts.append(groupedTexts[0] if groupedTexts else None)

        itemNames = []
        for sentence in gridGroupedTexts:
            if "Prime" in sentence:
                sentence = re.sub(r'\s+', '', sentence)
                sentence = re.sub(r'(\S)Prime(\S)', r'\1 Prime \2', sentence)
                sentence = re.sub(r'(\S)蓝图', r'\1 蓝图', sentence)
                itemNames.append(sentence)

    return itemNames

#process image in batch (all in the folder)
def processImages(imagePaths):
    itemList = []
    for item in imagePaths:
        itemListTemp = imageOcr(item)
        itemList.append(itemListTemp)

    itemList = np.array(itemList).flatten()
    return itemList

#search item server name using name from OCR
def getItemServerName(itemList):
    errorItems = []
    itemServerNames = []
    matchedNames = []
    for item in itemList:
        foundFlag = False
        for itemInfo in allItems:
            if fuzz.partial_ratio(itemInfo['item_name'], item) > 90:
                itemServerNames.append(itemInfo['url_name'])
                matchedNames.append(item)
                foundFlag = True
                break
        if not foundFlag:
            errorItems.append(item)
    return itemServerNames, matchedNames, errorItems

#get market info (plat is average of top 10 non-offline seller)
def getItemPlat(itemServerNames):
    result = []
    for item in itemServerNames:
        orderList = getWarframeMarketData(itemsList=[item], checkOrder=True)[item]['orders']
        filteredItems = [order for order in orderList if order['user']['status'] != 'offline' and order['order_type'] == 'sell']
        sortedItems = sorted(filteredItems, key=lambda x: x['platinum'])[:10]
        averagePlatinum = sum(order['platinum'] for order in sortedItems) / len(sortedItems)
        result.append(averagePlatinum)
    return result

#get item ducats info
def getItemDucats(itemServerNames, maxRetries=3, delay=2):
    result = []
    for key in itemServerNames:
        retries = 0
        while retries < maxRetries:
            try:
                ducatsData = getWarframeMarketData(itemsList=[key], checkItemInfo=True)
                if key in ducatsData:
                    itemInfo = ducatsData[key]['item']['items_in_set']
                    for item in itemInfo:
                        if item['url_name'] == key:
                            result.append(item.get('ducats', 0))
                            break
                else:
                    result.append(0)
                break
            except Exception as e:
                print(f"Error fetching ducats for {key}: {e}. Retrying...")
                retries += 1
                time.sleep(delay)
        else:
            result.append(0)
            print(f"Failed to fetch ducats for {key} after {maxRetries} retries.")
    return result


def selectFolder():
    folderSelected = filedialog.askdirectory()
    if folderSelected:
        folderPathVar.set(folderSelected)
        loadImages(folderSelected)

#load and process image, fetch data from WF market, then send data to UI
def loadImages(folderPath):
    try:
        imageFiles = [
            os.path.join(folderPath, f) for f in os.listdir(folderPath)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if not imageFiles:
            messagebox.showinfo("No Images Found", "The selected folder contains no PNG or JPG images.")
            return

        itemList = processImages(imageFiles)
        itemServerNames, matchedNames, errorItems = getItemServerName(itemList)
        itemPlat = getItemPlat(itemServerNames)
        itemDucats = getItemDucats(itemServerNames)
        df = pd.DataFrame({
            'name': matchedNames,
            'ducats': itemDucats,
            'platinum': itemPlat
        })
        
        df['ducats/platinum'] = df['ducats'] / df['platinum']
        df = df.sort_values(by='ducats/platinum', ascending=False)

        df.iloc[:, 1:] = df.iloc[:, 1:].applymap(lambda x: f"{x:.2f}")
        df = df.drop_duplicates(subset='name', keep='first')
        displayResults(df, errorItems)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# display data, double click or right click to copy cell
def displayResults(results, errorItems):
    for widget in resultsFrame.winfo_children():
        widget.destroy()

    tree = ttk.Treeview(resultsFrame, columns=list(results.columns), show="headings")
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    for col in results.columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=150)

    for _, row in results.iterrows():
        tree.insert("", "end", values=list(row))

    def copyCell(event):
        selectedItem = tree.selection()
        if selectedItem:
            columnIndex = tree.identify_column(event.x)[1:]
            rowIndex = tree.index(selectedItem[0])
            try:
                cellValue = results.iloc[rowIndex, int(columnIndex) - 1]
                root.clipboard_clear()
                root.clipboard_append(str(cellValue))
                root.update()
            except Exception as e:
                print(f"Error copying cell value: {e}")

    tree.bind("<Button-3>", copyCell)
    tree.bind("<Double-1>", copyCell)

    errorLabel = tk.Label(resultsFrame, text="Error Items:", font=("Helvetica", 10, "bold"))
    errorLabel.pack(fill="x", padx=5, pady=(10, 5))

    errorText = tk.Text(resultsFrame, height=1, wrap=tk.WORD, font=("Helvetica", 8))
    errorList = " | ".join(errorItems) if errorItems else "No errors found."
    errorText.insert(tk.END, errorList)
    errorText.config(state=tk.DISABLED)
    errorText.pack(fill="x", padx=5, pady=(5, 10))

root = tk.Tk()
root.title("Warframe 仓库清理助手")
root.geometry("1200x800")
allItems = getWarframeMarketData(initialize=True)

folderFrame = tk.Frame(root)
folderFrame.pack(fill="x", padx=10, pady=10)

folderPathVar = tk.StringVar()

folderLabel = tk.Label(folderFrame, text="Folder:")
folderLabel.pack(side="left")

folderEntry = tk.Entry(folderFrame, textvariable=folderPathVar, state="readonly", width=50)
folderEntry.pack(side="left", padx=5)

browseButton = tk.Button(folderFrame, text="Browse", command=selectFolder)
browseButton.pack(side="left", padx=5)

resultsFrame = tk.Frame(root, borderwidth=1, relief="sunken")
resultsFrame.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
