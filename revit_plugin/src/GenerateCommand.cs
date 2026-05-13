using System;
using System.IO;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace Architext.Revit
{
    [Transaction(TransactionMode.Manual)]
    public class GenerateCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            GenerateForm form = new GenerateForm();
            if (form.ShowDialog() != System.Windows.Forms.DialogResult.OK)
            {
                return Result.Cancelled;
            }

            try
            {
                TaskDialog.Show(
                    "ArchiText",
                    "Generating floor plan with " + form.GeneratorDisplayName + ".\n\nThis may take a few seconds.");

                ArchitextClient client = new ArchitextClient(form.BackendUrl);
                string jobId = client.StartGeneration(form.Prompt, form.GeneratorMode);
                client.WaitForCompletion(jobId, 180);

                string outDir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                    "Architext",
                    "Revit");

                Directory.CreateDirectory(outDir);
                string ifcPath = Path.Combine(outDir, "architext_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".ifc");
                client.DownloadIfc(jobId, ifcPath);

                string importMessage;
                bool imported = IfcImportHelper.ImportOrOpen(commandData.Application, ifcPath, out importMessage);

                TaskDialog.Show(
                    "ArchiText",
                    (imported ? "Generated and imported IFC successfully." : "Generated IFC successfully.") +
                    "\n\nFile:\n" + ifcPath +
                    "\n\n" + importMessage);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                TaskDialog.Show("ArchiText Error", ex.Message);
                return Result.Failed;
            }
        }
    }
}

