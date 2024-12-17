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
import logging
import time
import json

logging.disable(logging.DEBUG)
logging.disable(logging.WARNING)

ocr = PaddleOCR(lang="ch") 

#pull data from WF market

# Path to the local file where the Ducats data will be stored
ducatsFilePath = "./itemDucatsDictonary.json"

def loadDucatsData():
    if os.path.exists(ducatsFilePath):
        try:
            with open(ducatsFilePath, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading data from file: {e}")
    return {}

def saveDucatsData(ducatsData):
    try:
        with open(ducatsFilePath, 'w', encoding='utf-8') as file:
            json.dump(ducatsData, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error saving data to file: {e}")



def getWarframeMarketData(itemsList=[], checkOrder=False, checkItemInfo=False, initialize=None):
    baseUrl = "https://api.warframe.market/v1/items"
    results = {}
    maxRetries=5
    delay=0.5
    
    if initialize is not None:
        for attempt in range(maxRetries):
            try:
                response = requests.get(baseUrl, headers={"Language": "zh-hans"})
                if response.status_code == 200:
                    data = response.json()
                    if 'payload' in data:
                        return data['payload']['items']
                print(f"Initialization: Error {response.status_code}")
            except Exception as e:
                print(f"Initialization: Request failed - {e}")
                time.sleep(delay)
        return results
    
    for item in itemsList:
        if checkOrder:
            url = f"{baseUrl}/{item}/orders"
        elif checkItemInfo:
            url = f"{baseUrl}/{item}"
        else:
            return []

        for attempt in range(maxRetries):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    results[item] = data.get('payload', {})
                    break  # Exit retry loop on success
                else:
                    results[item] = f"Error {response.status_code}"
            except Exception as e:
                results[item] = f"Request failed - {e}"
                time.sleep(delay)

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

            # Perform OCR
            result = ocr.ocr(sectionArray, cls=True)

            # Ensure that result[0] contains data
            if not result or not result[0]:
                #gridGroupedTexts.append(None)
                continue

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

                result = "".join(elements)
                if "Prime" in result:
                    groupedTexts.append(result)

            gridGroupedTexts.append(groupedTexts[0] if groupedTexts else None)

    # Process grouped texts for "Prime" and other patterns
    itemNames = []
    for sentence in gridGroupedTexts:
        if sentence and "Prime" in sentence:
            sentence = re.sub(r"\s+", "", sentence)
            sentence = re.sub(r"(\S)Prime(\S)", r"\1 Prime \2", sentence)
            sentence = re.sub(r"(\S)蓝图", r"\1 蓝图", sentence)
            itemNames.append(sentence)
    print(f"finish processed image {imagePath}")
    print(f"Items in the image: {itemNames}")
    return itemNames


#process image in batch (all in the folder)
def processImages(imagePaths):
    itemList = []
    for item in imagePaths:
        itemListTemp = imageOcr(item)
        itemList.extend(itemListTemp)

    itemList = np.array(itemList).flatten()
    return itemList

#search item server name using name from OCR
def getItemServerName(itemList):
    try:
        errorItems = []
        itemServerNames = []
        matchedNames = []
        for item in itemList:
            foundFlag = False
            highestScore = -1
            score = -1
            tempitemServerName = ""
            tempmatchedName = ""
            for itemInfo in allItems:
                score = fuzz.ratio(itemInfo["item_name"].replace(" ",""), item.replace(" ",""))
                if score > highestScore and score > 80:
                    highestScore = score
                    tempitemServerName = itemInfo["url_name"]
                    tempmatchedName = item
                    foundFlag = True
            
            if foundFlag:
                itemServerNames.append(tempitemServerName)
                matchedNames.append(tempmatchedName)
            else:
                errorItems.append(item)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred in getItemServerName: {e}")
    return itemServerNames, matchedNames, errorItems

#get market info (plat is average of top 10 non-offline seller)
def getItemPlat(itemServerNames):
    try:
        result = []
        for item in itemServerNames:
            orderList = getWarframeMarketData(itemsList=[item], checkOrder=True)[item]["orders"]
            filteredItems = [order for order in orderList if order["user"]["status"] != "offline" and order["order_type"] == "sell"]
            sortedItems = sorted(filteredItems, key=lambda x: x["platinum"])[:10]
            averagePlatinum = sum(order["platinum"] for order in sortedItems) / len(sortedItems)
            result.append(averagePlatinum)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred in getItemPlat: {e}")
    return result

#get item ducats info from API/cached data
def getItemDucats(itemServerNames):
    try:
        ducatsDataDict = loadDucatsData()
        result = []
        
        for key in itemServerNames:
            if key in ducatsDataDict:
                print(f"Using cached data for {key}")
                result.append(ducatsDataDict[key])
            else:
                print(f"Fetching Ducats for {key}")
                ducatsData = getWarframeMarketData(itemsList=[key], checkItemInfo=True)
                
                if key in ducatsData:
                    itemInfo = ducatsData[key]["item"]["items_in_set"]
                    for item in itemInfo:
                        if item["url_name"] == key:
                            ducats = item.get("ducats", 0)
                            result.append(ducats)
                            ducatsDataDict[key] = ducats
                            break
                else:
                    result.append(0)
        
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred in getItemDucats: {e}")
        return []
    else:
        saveDucatsData(ducatsDataDict)
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
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        if not imageFiles:
            messagebox.showinfo("No Images Found", "The selected folder contains no PNG or JPG images.")
            return
        print("===============Processing images")
        timea = time.time()
        itemList = processImages(imageFiles)
        timeb = time.time()
        print(f"Elapsed time: {timeb - timea}")

        print("===============Getting server names")
        timea = time.time()
        itemServerNames, matchedNames, errorItems = getItemServerName(itemList)
        timeb = time.time()
        print(f"Elapsed time: {timeb - timea}")

        print("===============Checking sell orders")
        timea = time.time()
        itemPlat = getItemPlat(itemServerNames)
        timeb = time.time()

        print(f"Elapsed time: {timeb - timea}")
        print("===============Getting item info")
        timea = time.time()
        itemDucats = getItemDucats(itemServerNames)
        timeb = time.time()

        print(f"Elapsed time: {timeb - timea}")
        print(itemServerNames)
        print(len(matchedNames), matchedNames)
        print(len(itemDucats), itemDucats)
        print(len(itemPlat), itemPlat)
        df = pd.DataFrame({
            "name": matchedNames,
            "ducats": itemDucats,
            "platinum": itemPlat
        })
        
        df["ducats/platinum"] = df["ducats"] / df["platinum"]
        df = df.sort_values(by="ducats/platinum", ascending=False)

        df.iloc[:, 1:] = df.iloc[:, 1:].applymap(lambda x: f"{x:.2f}")
        df = df.drop_duplicates(subset="name", keep="first")
        displayResults(df, errorItems)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# display data, double click or right click to copy cell
def displayResults(results, errorItems):
    def sortByColumn(column):
        nonlocal results
        # Ensure the correct data type for numeric columns (convert to float)
        if column in ['ducats', 'platinum', 'ducats/platinum']:
            results[column] = results[column].astype(float)  # Convert to float (double precision)

        results = results.sort_values(by=column, ascending=False)
        updateTreeview()

    def updateTreeview():
        # Clear existing rows
        tree.delete(*tree.get_children())
        # Insert updated rows
        for _, row in results.iterrows():
            tree.insert("", "end", values=list(row))

    # Create a frame for the sorting buttons
    buttonFrame = tk.Frame(resultsFrame)
    buttonFrame.pack(fill="x", padx=5, pady=(10, 5))

    # Create buttons for each column
    for col in results.columns:
        btn = tk.Button(buttonFrame, text=f"Sort by {col}",
                        command=lambda c=col: sortByColumn(c))
        btn.pack(side="left", padx=5)

    # Create Treeview
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

    # Error Items Section
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



