# Setting up Support at Home statements

This program makes a PDF statement for each of your clients. It runs only on your computer.
Your client information is never sent over the internet.

You only need to do steps 1 to 3 once.

## 1. Install Python

1. Go to **python.org/downloads** and click the yellow **Download Python** button.
2. Open the file you downloaded.
3. On the first screen, **tick "Add python.exe to PATH"** at the bottom, then click **Install Now**.
4. When it says "Setup was successful", click **Close**.

If Windows offers to get Python from the **Microsoft Store**, say no. Use the python.org version.

## 2. Install ReportLab

ReportLab is the free add-on that creates the PDFs.

1. Click **Start**, type **cmd** and open **Command Prompt**.
2. Type this, then press **Enter**:

   ```
   py -m pip install reportlab
   ```

3. Wait until it says **Successfully installed**, then close the window.

## 3. Unblock the zip file

Windows may block programs that came from the internet or an email.

1. **Before you extract the zip**, right-click it and choose **Properties**.
2. At the bottom of the **General** tab, tick **Unblock**, then click **OK**.
   (If there's no Unblock box, the file is already fine.)

## 4. Extract and start

1. Right-click the zip and choose **Extract All…**, then **Extract**.
2. In the new folder, double-click **launch.pyw**.
3. The **Support at Home statements** window opens.

Each time after that, just double-click **launch.pyw**.

Tip: right-click **launch.pyw** → **Show more options** → **Send to** → **Desktop (create shortcut)**.

## Using it

1. **Clients file**: click **Browse…** and choose your clients CSV.
2. **Line items file**: click **Browse…** and choose your line items CSV.
3. **Save statements to**: choose where the PDFs should go. The default is the `statements` folder.
4. Click **Create statements**.

You can keep using your computer while it works. When it finishes it tells you how many statements
were created. Any rows with a problem are skipped, shown in red, and listed in the **error log**.
Fix them in your spreadsheet and run it again.

The window remembers your files for next time. To start again, click **Reset**: it clears the list
and goes back to the sample files. Statements you've already created are not deleted.

To use your own logo, put a square PNG or JPG named `logo.png` (or `logo.jpg`) in the `branding` folder.
It must be at least 300 x 300 pixels.

Your business name, address and contact details at the top of every page come from
`branding\provider.csv`. Open it in Excel, replace the sample details with yours (one row), and save it as
**CSV UTF-8**. Only `provider_name` is required; leave any other column blank to hide it.
Columns: `provider_name, addr1, addr2, addr3, phone, email, website, abn`.

## If something goes wrong

**Double-clicking launch.pyw opens Notepad or asks "How do you want to open this file?"**
Python isn't installed, or wasn't installed from python.org. Do step 1 again. Then right-click
`launch.pyw` → **Open with** → **Choose another app** → **Python**, and tick **Always**.

**"Python was not found" in Command Prompt, or the Microsoft Store opens**
Python isn't installed, or "Add python.exe to PATH" wasn't ticked. Run the python.org installer again,
choose **Modify**, and make sure **Add Python to environment variables** is ticked. Then close and reopen Command Prompt.

**"ReportLab is not installed" (or "Pillow is not installed")**
Do step 2 again. If the message says Pillow, type `py -m pip install pillow` instead.

**"Logo error: … is not a readable image file"**
The logo file is damaged, or isn't really a picture. Save it again from your design program as PNG.

**"Logo error: logo must be PNG or JPG"**
Save the logo as PNG or JPG. Other formats (such as .webp, .gif or .bmp renamed to .png) won't work.

**"Logo error: logo must be at least 300 x 300 pixels"**
The logo is too small and would look blurry. Use a larger version.

**"Logo error: logo must be roughly square"**
Crop or pad the logo so it's about as wide as it is tall.

No logo at all? That's fine: remove the file from the `branding` folder and statements are made without one.

**"Provider details error: …"**
Check `branding\provider.csv`: the first row must have the column names (including `provider_name`),
the second row your details, and it must be saved as **CSV UTF-8**. Close it in Excel before creating statements.

**"The clients file is missing these columns…"**
You may have picked the wrong file, or a column was renamed. The first row must have the column names
exactly as in the sample `clients.csv`.

**"… is not a date (use DD-MM-YYYY)"**
Write dates day first, for example `01-01-2026` or `1/01/2026` (as Excel shows Australian dates).
Check the day and month aren't swapped, and that the date exists (there's no 31-02-2026).

**"…isn't saved as UTF-8"**
In Excel choose **File → Save As**, and pick **CSV UTF-8 (Comma delimited)**.

**"Windows didn't allow access to a file"**
A CSV or PDF is open in Excel or a PDF viewer. Close it and try again.

**Windows says "Windows protected your PC"**
Click **More info**, then **Run anyway**. To stop it happening, do step 3 (Unblock) with the original zip.

**Anything else**
The window shows a message and saves the details to a file named `crash.log`. To find it, press
**Windows key + R**, type `%LOCALAPPDATA%\SAHStatements` and press Enter. Send `crash.log` to whoever set this up for you.
Open it in Notepad first: if the error involved a client, their name or ID may appear in it.
