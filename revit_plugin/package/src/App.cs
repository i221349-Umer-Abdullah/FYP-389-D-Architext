using System;
using System.Reflection;
using Autodesk.Revit.UI;

namespace Architext.Revit
{
    public class App : IExternalApplication
    {
        public Result OnStartup(UIControlledApplication application)
        {
            try
            {
                RibbonPanel panel = GetOrCreatePanel(application, "ArchiText");
                string assemblyPath = Assembly.GetExecutingAssembly().Location;

                PushButtonData buttonData = new PushButtonData(
                    "ArchitextGenerate",
                    "Generate\nFloor Plan",
                    assemblyPath,
                    "Architext.Revit.GenerateCommand");

                buttonData.ToolTip = "Generate an ArchiText floor plan using the local FastAPI backend and import the IFC into Revit.";
                panel.AddItem(buttonData);
            }
            catch (Exception ex)
            {
                TaskDialog.Show("ArchiText", "Failed to create ArchiText ribbon panel:\n" + ex.Message);
            }

            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication application)
        {
            return Result.Succeeded;
        }

        private static RibbonPanel GetOrCreatePanel(UIControlledApplication application, string name)
        {
            foreach (RibbonPanel panel in application.GetRibbonPanels())
            {
                if (panel.Name == name)
                {
                    return panel;
                }
            }

            return application.CreateRibbonPanel(name);
        }
    }
}

